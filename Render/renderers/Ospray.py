# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2021 Howetuft <howetuft@gmail.com>                      *
# *   Copyright (c) 2023 Howetuft <howetuft@gmail.com>                      *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2.1 of   *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   This program is distributed in the hope that it will be useful,       *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Library General Public License for more details.                  *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with this program; if not, write to the Free Software   *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *   USA                                                                   *
# *                                                                         *
# ***************************************************************************

"""OSPRay studio renderer plugin for FreeCAD Render workbench."""

# NOTE: no SDL documentation seems to exist for ospray_studio, so below
# functions have been elaborated by reverse engineering.
# SDL format is JSON
# Suggested documentation links:
# https://github.com/ospray/ospray_studio
#
# Please note coordinate systems are different between fcd and osp:
#
# FreeCAD (z is up):         Ospray (y is up):
#
#
#  z  y                         y
#  | /                          |
#  .--x                         .--x
#                              /
#                             z
#

import json
import os
import os.path
from math import degrees, asin, sqrt, atan2, radians

import FreeCAD as App

# Transformation from fcd coords to osp coords
PLACEMENT = App.Placement(
    App.Matrix(1, 0, 0, 0, 0, 0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1)
)

TEMPLATE_FILTER = "Ospray templates (ospray_*.sg)"

DISNEY_IOR = 1.5

# ===========================================================================
#                             Write functions
# ===========================================================================


def write_mesh(name, mesh, material, **kwargs):
    """Compute a string in renderer SDL to represent a FreeCAD mesh."""
    # Material values
    matval = material.get_material_values(
        name,
        _write_texture,
        _write_value,
        _write_texref,
        kwargs["project_directory"],
        kwargs["object_directory"],
    )

    # Write the mesh as an OBJ tempfile
    objfile = mesh.write_file(
        name,
        mesh.ExportType.OBJ,
        mtlcontent=_write_material(name, matval),
    )

    # Compute OBJ transformation
    # including transfo from FCD coordinates to ospray ones
    osp_placement = PLACEMENT.copy()
    mesh.transformation.apply_placement(osp_placement, left=True)

    # Node and transform names
    # Very important: keep them as is, as they are hard-coded in ospray...
    basename = os.path.basename(objfile)
    basename = basename.encode("unicode_escape").decode("utf-8")
    nodename, _ = os.path.splitext(basename)
    nodename = f"{nodename}_importer"
    transform_name, _ = os.path.splitext(basename)
    transform_name = f"{transform_name}_rootXfm"

    # Compute transformation components
    transfo = mesh.transformation
    translation = ", ".join(str(v) for v in transfo.get_translation())
    rotation = ", ".join(
        f'"{k}": {v}' for k, v in zip("ijkr", transfo.get_rotation_qtn())
    )
    scale = ", ".join(str(v) for v in transfo.get_scale_vector())

    snippet_obj = f"""
      {{
        "name": {json.dumps(nodename)},
        "type": "IMPORTER",
        "filename": {json.dumps(objfile)},
        "children": [
            {{
                "name":{json.dumps(transform_name)},
                "type":"TRANSFORM",
                "subType": "transform",
                "value": {{
                    "linear": {{
                        "x":[1.0, 0.0, 0.0],
                        "y":[0.0, 1.0, 0.0],
                        "z":[0.0, 0.0, 1.0]
                    }},
                    "affine": [0.0,0.0,0.0]
                }},
                "children": [
                    {{
                        "name":"translation",
                        "type":"PARAMETER",
                        "subType":"vec3f",
                        "sgOnly":false,
                        "value":[{translation}]
                    }},
                    {{
                        "name":"rotation",
                        "type":"PARAMETER",
                        "subType":"quaternionf",
                        "sgOnly":false,
                        "value": {{ {rotation} }}
                    }},
                    {{
                        "name":"scale",
                        "type":"PARAMETER",
                        "subType":"vec3f",
                        "sgOnly":false,
                        "value": [{scale}]
                    }}
                ]
            }}
        ]
      }},"""
    return snippet_obj


def write_camera(name, pos, updir, target, fov, resolution, **kwargs):
    """Compute a string in renderer SDL to represent a camera."""
    # OSP camera's default orientation is target=(0, 0, -1), up=(0, 1, 0),
    # in osp coords.
    # At this time (12-30-2022), fovy parameter is not serviceable in
    # sg camera
    # As a workaround, we use a gltf file...

    plc = PLACEMENT.multiply(pos)
    base = plc.Base
    rot = plc.Rotation.Q
    fov = radians(fov)
    width, height = resolution
    aratio = width / height

    gltf_snippet = f"""
{{
  "asset": {{
    "generator": "FreeCAD Render Workbench",
    "version": "2.0"
  }},
  "scene": 0,
  "scenes": [
    {{
      "name": "scene",
      "nodes": [0]
    }}
  ],
  "cameras" : [
    {{
      "name": "{name}",
      "type": "perspective",
      "perspective": {{
        "yfov": {fov},
        "znear": 0.0,
        "aspectRatio" : {aratio}
      }}
    }}
  ],
  "nodes" : [
    {{
      "translation" : [ {base.x}, {base.y}, {base.z} ],
      "rotation" : [ {rot[0]}, {rot[1]}, {rot[2]}, {rot[3]} ],
      "camera" : 0
    }}
  ]
}}
"""
    gltf_file, gltf_file_rel = _new_object_file_path(name, "gltf", **kwargs)

    with open(gltf_file, "w", encoding="utf-8") as f:
        f.write(gltf_snippet)

    snippet = f"""
      {{
        "name": {json.dumps(name)},
        "type": "IMPORTER",
        "filename": {json.dumps(gltf_file_rel)},
        "freecadtype" : "camera"
      }},"""
    return snippet


def write_pointlight(name, pos, color, power, **kwargs):
    """Compute a string in renderer SDL to represent a point light."""
    # Tip: in studio, to visualize where the light is, increase the radius

    snippet = """
      {{
        "name": "lights",
        "type": "LIGHTS",
        "subType": "lights",
        "children": [
          {{
            "name": {n},
            "type": "LIGHT",
            "subType": "sphere",
            "children": [
              {{
                "name": "visible",
                "description": "whether the light can be seen directly",
                "sgOnly": false,
                "subType": "bool",
                "type": "PARAMETER",
                "value": true
              }},
              {{
                "name": "intensity",
                "description": "intensity of the light (a factor)",
                "sgOnly": false,
                "subType": "float",
                "type": "PARAMETER",
                "value": {s}
              }},
              {{
                "name": "color",
                "description": "color of the light",
                "sgOnly": false,
                "subType": "rgb",
                "type": "PARAMETER",
                "value": [{c[0]}, {c[1]}, {c[2]}]
              }},
              {{
                "name": "position",
                "description": "position of the light",
                "sgOnly": false,
                "subType": "vec3f",
                "type": "PARAMETER",
                "value": [{p[0]}, {p[1]}, {p[2]}]
              }}
            ]
          }}
        ]
      }},"""
    osp_pos = PLACEMENT.multVec(pos)
    return snippet.format(
        n=json.dumps(name), c=color.to_linear(), p=osp_pos, s=power
    )


def write_arealight(
    name, pos, size_u, size_v, color, power, transparent, **kwargs
):
    """Compute a string in renderer SDL to represent an area light."""
    # Note: ospray expects a radiance (W/m²), we have to convert power
    # See here: https://www.ospray.org/documentation.html#luminous

    # Write mtl file (material)
    radiance = power / (size_u * size_v)
    radiance /= 1000  # Magic number
    transparency = 1.0 if transparent else 0.0
    lcol = color.to_linear()
    mtl = f"""
# Created by FreeCAD <https://FreeCAD.Org>",
newmtl material
type luminous
color {lcol[0]} {lcol[1]} {lcol[2]}
intensity {radiance}
transparency {transparency}
"""
    mtl_file, _ = _new_object_file_path(name, "mtl", **kwargs)
    with open(mtl_file, "w", encoding="utf-8") as f:
        f.write(mtl)

    # Write obj file (geometry)
    osp_pos = PLACEMENT.multiply(pos)
    verts = [
        (-size_u, -size_v, 0),
        (+size_u, -size_v, 0),
        (+size_u, +size_v, 0),
        (-size_u, +size_v, 0),
    ]
    verts = [osp_pos.multVec(App.Vector(*v)) for v in verts]
    verts = [f"v {v.x} {v.y} {v.z}" for v in verts]
    verts = "\n".join(verts)
    normal = osp_pos.multVec(App.Vector(0, 0, 1))

    obj = f"""
# Created by FreeCAD <https://FreeCAD.Org>"]
mtllib {os.path.basename(mtl_file)}
{verts}
vn {normal.x} {normal.y} {normal.z}
o {name}
usemtl material
f 1//1 2//1 3//1 4//1
"""

    obj_file, obj_file_rel = _new_object_file_path(name, "obj", **kwargs)
    with open(obj_file, "w", encoding="utf-8") as f:
        f.write(obj)

    # Return SDL
    snippet = f"""
      {{
        "name": {json.dumps(name)},
        "type": "IMPORTER",
        "filename": {json.dumps(obj_file_rel)}
      }},"""

    return snippet


def write_sunskylight(
    name,
    direction,
    distance,
    turbidity,
    albedo,
    sun_intensity,
    sky_intensity,
    **kwargs,
):
    """Compute a string in renderer SDL to represent a sunsky light."""
    # We make angle calculations in osp's coordinates system
    # By default, Up is (0,1,0), Right is (1,0,0), and:
    #  - North (0°) is z (0, 0, 1)
    #  - East (90°) is x (1, 0, 0)
    #  - South (180°) is -z (0, 0, -1)
    #  - West (270°) is -x (-1, 0, 0)
    # We'll compute elevation and azimuth accordingly...

    _dir = PLACEMENT.multVec(App.Vector(direction))
    elevation = asin(_dir.y / sqrt(_dir.x**2 + _dir.y**2 + _dir.z**2))
    azimuth = atan2(_dir.x, _dir.z)
    intensity = sun_intensity * 0.05
    if sky_intensity != 1.0:
        msg = (
            "[Render][Ospray] - WARNING: sunsky light - sky intensity "
            "is not supported (should be kept at 1.0)."
        )
        print(msg)
    snippet = f"""
      {{
        "description": "Lights",
        "name": "lights",
        "subType": "lights",
        "type": "LIGHTS",
        "children": [
          {{
            "name": {json.dumps(name)},
            "description": "Sunsky light",
            "type": "LIGHT",
            "subType": "sunSky",
            "children": [
              {{
                "description": "whether the light can be seen directly",
                "name": "visible",
                "sgOnly": false,
                "subType": "bool",
                "type": "PARAMETER",
                "value": true
              }},
              {{
                "description": "intensity of the light (a factor)",
                "name": "intensity",
                "sgOnly": false,
                "subType": "float",
                "type": "PARAMETER",
                "value": {intensity}
              }},
              {{
                "description": "color of the light",
                "name": "color",
                "sgOnly": false,
                "subType": "rgb",
                "type": "PARAMETER",
                "value": [1.0, 1.0, 1.0]
              }},
              {{
                "description": "OSPRay light type",
                "name": "type",
                "sgOnly": true,
                "subType": "string",
                "type": "PARAMETER",
                "value": "sunSky"
              }},
              {{
                "description": "Up direction",
                "name": "up",
                "sgOnly": false,
                "subType": "vec3f",
                "type": "PARAMETER",
                "value": [0.0, 1.0, 0.0]
              }},
              {{
                "description": "Right direction",
                "name": "right",
                "sgOnly": true,
                "subType": "vec3f",
                "type": "PARAMETER",
                "value": [1.0, 0.0, 0.0]
              }},
              {{
                "description": "Angle to horizon",
                "name": "elevation",
                "sgOnly": true,
                "subType": "float",
                "type": "PARAMETER",
                "value": {degrees(elevation)}
              }},
              {{
                "description": "Angle to North",
                "name": "azimuth",
                "sgOnly": true,
                "subType": "float",
                "type": "PARAMETER",
                "value": {degrees(azimuth)}
              }},
              {{
                "description": "Turbidity",
                "name": "turbidity",
                "sgOnly": false,
                "subType": "float",
                "type": "PARAMETER",
                "value": {turbidity}
              }},
              {{
                "description": "Ground albedo",
                "name": "albedo",
                "sgOnly": false,
                "subType": "float",
                "type": "PARAMETER",
                "value": {albedo}
              }}
            ]
          }}
        ]
      }},"""
    return snippet


def write_imagelight(name, image, **kwargs):
    """Compute a string in renderer SDL to represent an image-based light."""
    # At this time (02-15-2021), in current version (0.6.0),
    # texture import is not serviceable in OspStudio - see here:
    # https://github.com/ospray/ospray_studio/blob/release-0.6.x/sg/JSONDefs.h#L107
    # As a workaround, we use a gltf file...

    gltf_snippet = """
{{
  "asset": {{
    "generator": "FreeCAD Render Workbench",
    "version": "2.0"
  }},
  "scene": 0,
  "scenes": [
    {{
      "name": "scene",
      "nodes": []
    }}
  ],
  "extensions": {{
    "BIT_scene_background" : {{
      "background-uri": {f},
      "rotation": [0, 0.7071067811865475, 0, 0.7071067811865475 ]
    }}
  }}
}}
"""
    gltf_file, gltf_file_rel = _new_object_file_path(name, "gltf", **kwargs)

    # osp requires the hdr file path to be relative from the gltf file path
    # (see GLTFData::createLights insg/importer/glTF.cpp, ),
    # so we have to manipulate paths a bit...
    image_relpath = os.path.relpath(image, os.path.dirname(gltf_file))

    with open(gltf_file, "w", encoding="utf-8") as f:
        f.write(gltf_snippet.format(f=json.dumps(image_relpath)))

    gltf_file = os.path.basename(gltf_file)
    snippet = f"""
      {{
        "name": {json.dumps(name)},
        "type": "IMPORTER",
        "filename": {json.dumps(gltf_file_rel)}
      }},"""
    return snippet


def write_distantlight(
    name,
    color,
    power,
    direction,
    angle,
    **_,
):
    """Compute a string in renderer SDL to represent a distant light."""

    snippet = """
      {{
        "name": "lights",
        "type": "LIGHTS",
        "subType": "lights",
        "children": [
          {{
            "name": {n},
            "type": "LIGHT",
            "subType": "distant",
            "children": [
              {{
                "name": "visible",
                "description": "whether the light can be seen directly",
                "sgOnly": false,
                "subType": "bool",
                "type": "PARAMETER",
                "value": true
              }},
              {{
                "name": "intensity",
                "description": "intensity of the light (a factor)",
                "sgOnly": false,
                "subType": "float",
                "type": "PARAMETER",
                "value": {s}
              }},
              {{
                "name": "color",
                "description": "color of the light",
                "sgOnly": false,
                "subType": "rgb",
                "type": "PARAMETER",
                "value": [{c[0]}, {c[1]}, {c[2]}]
              }},
              {{
                "name": "angularDiameter",
                "subType": "float",
                "type": "PARAMETER",
                "value": {a}
              }},
              {{
                "name": "direction",
                "subType": "vec3f",
                "type": "PARAMETER",
                "value": [{d.x}, {d.y}, {d.z}]
              }}
            ]
          }}
        ]
      }},"""
    osp_dir = PLACEMENT.multVec(direction)
    return snippet.format(
        n=json.dumps(name), c=color.to_linear(), d=osp_dir, s=power, a=angle
    )


# ===========================================================================
#                              Material implementation
# ===========================================================================


def _write_material(name, matval):
    """Compute a string in the renderer SDL, to represent a material.

    This function should never fail: if the material is not recognized,
    a fallback material is provided.
    """
    try:
        material_function = MATERIALS[matval.shadertype]
    except KeyError:
        msg = (
            "'{}' - Material '{}' unknown by renderer, using fallback "
            "material\n"
        )
        App.Console.PrintWarning(msg.format(name, matval.shadertype))
        snippet_mat = _write_material_fallback(name, matval.default_color)
    else:
        snippet_mat = [
            material_function(name, matval),
            matval.write_textures(),
        ]
        snippet_mat = "".join(snippet_mat)

    return snippet_mat


def _write_material_passthrough(name, matval):
    """Compute a string in the renderer SDL for a passthrough material."""
    texture = matval.passthrough_texture
    snippet = "\n# Passthrough\n" + matval["string"]
    return snippet.format(
        n=name, c=matval.default_color.to_linear(), tex=texture
    )


def _write_material_glass(name, matval):  # pylint: disable=unused-argument
    """Compute a string in the renderer SDL for a glass material."""
    snippet = f"""
# Glass
type principled
{matval["ior"]}
{matval["color"]}
transmission 1
specular 1
metallic 0
diffuse 0
opacity 1
{matval["normal"] if matval.has_normal() else ""}
"""
    return snippet


def _write_material_disney(name, matval):  # pylint: disable=unused-argument
    """Compute a string in the renderer SDL for a Disney material."""
    # Nota1: OSP Principled material does not handle SSS, nor specular tint
    # Nota2: if metallic is set, specular should be 1.0. See here:
    # https://github.com/ospray/ospray_studio/issues/5
    snippet = f"""
# Disney
type principled
{matval["basecolor"]}
# No subsurface scattering (Ospray limitation)
{matval["metallic"]}
{matval["specular"]}
# No specular tint (Ospray limitation)
{matval["roughness"]}
{matval["anisotropic"]}
{matval["sheen"]}
{matval["sheentint"]}
{matval["clearcoat"]}
{matval["clearcoatgloss"]}
{matval["normal"] if matval.has_normal() else ""}
ior {DISNEY_IOR}
coatIor {DISNEY_IOR}
"""
    return snippet


def _write_material_pbr(name, matval):
    """Compute a string in the renderer SDL for a Disney material."""
    # Nota: if metallic is set, specular should be 1.0. See here:
    # https://github.com/ospray/ospray_studio/issues/5
    snippet = f"""
# Pbr ('{name}')
type principled
{matval["basecolor"]}
# No subsurface scattering (Ospray limitation)
{matval["metallic"]}
{matval["specular"]}
{matval["roughness"]}
{matval["normal"] if matval.has_normal() else ""}
"""
    return snippet


def _write_material_diffuse(name, matval):  # pylint: disable=unused-argument
    """Compute a string in the renderer SDL for a Diffuse material."""
    snippet = f"""
# Diffuse
type principled
{matval["color"]}
metallic 0
specular 0
diffuse 1
{matval["normal"] if matval.has_normal() else ""}
"""
    return snippet


def _write_material_mixed(name, matval):
    """Compute a string in the renderer SDL for a Mixed material."""
    # Glass
    submat_g = matval.getmixedsubmat("glass", name + "_glass")
    snippet_g_tex = submat_g.write_textures()

    # Diffuse
    submat_d = matval.getmixedsubmat("diffuse", name + "_diffuse")
    snippet_d_tex = submat_d.write_textures()

    transparency = matval.material.mixed.transparency
    assert isinstance(transparency, float)

    snippet_mix = f"""
# Mixed
type principled
{submat_d["color"]}
{submat_g["ior"]}
transmission {transparency}
{submat_g["color"]}
opacity {1 - transparency}
specular 0.5
{matval["normal"] if matval.has_normal() else ""}
"""
    snippet = [snippet_mix, snippet_d_tex, snippet_g_tex]
    return "".join(snippet)


def _write_material_carpaint(name, matval):  # pylint: disable=unused-argument
    """Compute a string in the renderer SDL for a carpaint material."""
    snippet = f"""
# Carpaint
type carPaint
{matval["basecolor"]}
{matval["normal"] if matval.has_normal() else ""}
"""
    return snippet


def _write_material_fallback(name, matval):
    """Compute a string in the renderer SDL for a fallback material.

    Fallback material is a simple Diffuse material.
    """
    try:
        lcol = matval.default_color.to_linear()
        red = float(lcol[0])
        grn = float(lcol[1])
        blu = float(lcol[2])
        assert (0 <= red <= 1) and (0 <= grn <= 1) and (0 <= blu <= 1)
    except (AttributeError, ValueError, TypeError, AssertionError):
        red, grn, blu = 1, 1, 1
    snippet = """
# Fallback
type obj
kd {r} {g} {b}
ns 2
"""
    return snippet.format(n=name, r=red, g=grn, b=blu)


def _write_material_emission(name, matval):
    """Compute a string in the renderer SDL for a Emission material."""
    snippet = f"""
# Emission ('{name}')
type luminous
{matval["color"]}
{matval["power"]}
transparency 0.0
"""
    return snippet


MATERIALS = {
    "Passthrough": _write_material_passthrough,
    "Glass": _write_material_glass,
    "Disney": _write_material_disney,
    "Diffuse": _write_material_diffuse,
    "Mixed": _write_material_mixed,
    "Carpaint": _write_material_carpaint,
    "Substance_PBR": _write_material_pbr,
    "Emission": _write_material_emission,
}


# ===========================================================================
#                              Textures
# ===========================================================================

# Field mapping from internal materials to OBJ ones (only for non trivial)
# None will exclude
_FIELD_MAPPING = {
    ("Diffuse", "color"): "baseColor",
    ("Diffuse", "bump"): None,
    ("Diffuse", "displacement"): None,
    ("Substance_PBR", "basecolor"): "baseColor",
    ("Substance_PBR", "bump"): None,
    ("Disney", "basecolor"): "baseColor",
    ("Disney", "subsurface"): "",
    ("Disney", "speculartint"): "",
    ("Disney", "anisotropic"): "anisotropy",
    ("Disney", "sheentint"): "sheenTint",
    ("Disney", "clearcoat"): "coat",
    ("Disney", "clearcoatgloss"): "coatRoughness",
    ("Disney", "bump"): None,
    ("Disney", "displacement"): None,
    ("Glass", "color"): "transmissionColor",
    ("Glass", "ior"): "ior",
    ("Glass", "bump"): None,
    ("Glass", "displacement"): None,
    ("Carpaint", "basecolor"): "baseColor",
    ("Mixed", "transparency"): "transmission",
    ("Mixed", "diffuse"): "",
    ("Mixed", "shader"): "",
    ("Mixed", "glass"): "",
    ("Mixed", "bump"): None,
    ("Mixed", "displacement"): None,
    ("glass", "color"): "transmissionColor",
    ("diffuse", "color"): "baseColor",
    ("Emission", "power"): "intensity",
    ("Passthrough", "string"): "",
    ("Passthrough", "renderer"): "",
}


def _write_texture(**kwargs):
    """Compute a string in renderer SDL to describe a texture.

    The texture is computed from a property of a shader (as the texture is
    always integrated into a shader). Property's data are expected as
    arguments.

    Args:
        objname -- Object name for which the texture is computed
        propname -- Name of the shader property
        propvalue -- Value of the shader property

    Returns:
        the name of the texture
        the SDL string of the texture
    """
    # Retrieve material parameters
    proptype = kwargs["proptype"]
    propname = kwargs["propname"]
    shadertype = kwargs["shadertype"]
    propvalue = kwargs["propvalue"]
    objname = kwargs["objname"]
    object_directory = kwargs["object_directory"]

    # Get texture parameters
    filename = os.path.relpath(propvalue.file, object_directory)
    scale, rotation = float(propvalue.scale), float(propvalue.rotation)
    translation_u = float(propvalue.translation_u)
    translation_v = float(propvalue.translation_v)

    # Exclusions (not supported)
    if (field := _FIELD_MAPPING.get((shadertype, propname), propname)) is None:
        return propname, ""
    if propname in [
        "clearcoatgloss",
        "ior",
        "subsurface",
        "speculartint",
        "bump",
        "displacement",
    ]:
        msg = (
            f"[Render] [Ospray] [{objname}] Warning: texture for "
            f"'{shadertype}::{propname}' "
            f"is not supported by Ospray. Falling back to default value.\n"
        )
        App.Console.PrintWarning(msg)
        return propname, ""

    # Snippets for texref
    if proptype in ["RGB", "float", "texonly", "texscalar"]:
        tex = [
            f"# Texture {field}",
            f"map_{field} {filename}",
            f"map_{field}.rotation {rotation}",
            f"map_{field}.scale {scale} {scale}",
            f"map_{field}.translation {translation_u} {translation_v}",
        ]
        tex = "\n".join(tex)
    elif proptype == "node":
        tex = ""
    else:
        raise NotImplementedError(proptype)

    return propname, tex


def _write_value(**kwargs):
    """Compute a string in renderer SDL from a shader property value.

    Args:
        proptype -- Shader property's type
        propvalue -- Shader property's value

    The result depends on the type of the value...
    """
    # Retrieve parameters
    proptype = kwargs["proptype"]
    propname = kwargs["propname"]
    shadertype = kwargs["shadertype"]
    val = kwargs["propvalue"]
    objname = kwargs["objname"]
    matval = kwargs["matval"]

    # Exclusions
    if (field := _FIELD_MAPPING.get((shadertype, propname), propname)) is None:
        msg = (
            f"[Render] [Ospray] [{objname}] Warning: "
            f"'{shadertype}::{propname}' is not supported by Ospray. "
            f"Skipping...\n"
        )
        App.Console.PrintWarning(msg)
        return ""

    # Special cases
    if propname == "clearcoatgloss":
        val = 1 - val
    if propname == "specular":
        # We have to test "metallic" in order to set specular...
        try:
            metallic = matval.material.shaderproperties["metallic"]
        except KeyError:
            # No metallic parameter
            pass
        else:
            if hasattr(metallic, "is_texture") or float(metallic):
                # metallic is a texture or a non-zero value:
                # specular must be set to something <> 0
                val = metallic if val <= 0.0 else val

    # Snippets for values
    if proptype == "RGB":
        lcol = val.to_linear()
        value = f"{field} {lcol[0]:.8} {lcol[1]:.8} {lcol[2]:.8}"
    elif proptype == "float":
        value = f"{field} {val:.8}"
    elif proptype == "node":
        value = ""
    elif proptype == "RGBA":
        lcol = val.to_linear()
        value = f"{field} {lcol[0]:.8} {lcol[1]:.8} {lcol[2]:.8} {lcol[3]:.8}"
    elif proptype == "str":
        value = f"{field} {val}"
    else:
        raise NotImplementedError

    return value


def _write_texref(**kwargs):
    """Compute a string in SDL for a reference to a texture in a shader."""
    # Retrieve parameters
    proptype = kwargs["proptype"]
    propname = kwargs["propname"]
    shadertype = kwargs["shadertype"]
    objname = kwargs["objname"]
    matval = kwargs["matval"]

    # Exclusions
    if (field := _FIELD_MAPPING.get((shadertype, propname), propname)) is None:
        msg = (
            f"[Render] [Ospray] [{objname}] Warning: "
            f"'{shadertype}::{propname}' is not supported by Ospray. "
            f"Skipping...\n"
        )
        App.Console.PrintWarning(msg)
        return ""
    if propname in ["clearcoatgloss", "ior"]:
        return f"{field} 1.5" if propname == "ior" else f"{field} 1.0"

    # Snippets for values
    if proptype == "RGB":
        value = f"{field} 1.0 1.0 1.0"
    elif proptype == "float":
        value = f"{field} 1.0"
    elif proptype == "node":
        value = f"{field} 1.0"
    elif proptype == "RGBA":
        value = f"{field} 1.0 1.0 1.0 1.0"
    elif proptype == "texonly":
        value = f"{field} 4.0" if propname == "normal" else f"{field} 1.0"
    elif proptype == "texscalar":
        normal_factor = matval.get_normal_factor()
        bump_factor = matval.get_bump_factor()
        value = (
            f"{field} {normal_factor}"
            if propname == "normal"
            else f"{field} {bump_factor}"
        )
    else:
        raise NotImplementedError(proptype)

    return value


# ===========================================================================
#                              Test function
# ===========================================================================


def test_cmdline(_):
    """Generate a command line for test.

    This function allows to test if renderer settings (path...) are correct
    """
    params = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Render")
    rpath = params.GetString("OspPath", "")
    return [rpath, "--help"]


# ===========================================================================
#                              Render function
# ===========================================================================


def render(
    project,
    prefix,
    batch,
    input_file,
    output_file,
    width,
    height,
    spp,
    denoise,
):
    """Generate renderer command.

    Args:
        project -- The project to render
        prefix -- A prefix string for call (will be inserted before path to
            renderer)
        batch -- A boolean indicating whether to call UI (false) or console
            (true) version of renderer
        input_file -- path to input file
        output -- path to output file
        width -- Rendered image width, in pixels
        height -- Rendered image height, in pixels
        spp -- Max samples per pixel (halt condition)
        denoise -- Flag to run denoiser

    Returns:
        The command to run renderer (string)
        A path to output image file (string)
    """

    def enclose_rpath(rpath):
        """Enclose rpath in quotes, if needed."""
        if not rpath:
            return ""
        if rpath[0] == rpath[-1] == '"':
            # Already enclosed (double quotes)
            return rpath
        if rpath[0] == rpath[-1] == "'":
            # Already enclosed (simple quotes)
            return rpath
        return f'"{rpath}"'

    # Read scene_graph (json)
    with open(input_file, "r", encoding="utf8") as f:
        scene_graph = json.load(f)

    # Keep only last cam
    _render_keep1cam(scene_graph)

    # Merge light groups
    _render_mergelightgroups(scene_graph)

    # Write reformatted input to file
    with open(input_file, "w", encoding="utf8") as f:
        json.dump(scene_graph, f, indent=2)

    # Prepare osp output file name
    # Osp renames the output file when writing, so we have to ask it to write a
    # specific file but we'll return the actual file written (we recompute the
    # name)
    # Nota: as a consequence, we cannot take user choice for output file into
    # account
    outfile_for_osp = os.path.join(App.getUserCachePath(), "ospray_out")
    if not batch:
        outfile_actual = f"{outfile_for_osp}.00000.png"  # The file osp'll use
    else:
        outfile_actual = (
            f"{outfile_for_osp}.Camera_1.00000.png"  # The file osp'll use
        )
    # We remove the outfile before writing, otherwise ospray will choose
    # another file
    try:
        os.remove(outfile_actual)
    except FileNotFoundError:
        # The file does not already exist: no problem
        pass

    # Prepare command line arguments
    params = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Render")
    if prefix := params.GetString("Prefix", ""):
        prefix += " "
    rpath = params.GetString("OspPath", "")

    args = ""
    if batch:
        args += '"batch" '
        args += " --camera 1 "
    args += params.GetString("OspParameters", "")
    args += f" --resolution {width}x{height} "
    if output_file:
        args += f'  --image "{outfile_for_osp}"'
        if not batch:
            args += "  --saveImageOnExit"
    if spp:
        args += f"  --accumLimit {spp} --spp 1 "
    if denoise:
        args += " --denoiser "
        if spp:
            args += " --denoiseFinalFrame "

    if not rpath:
        App.Console.PrintError(
            "Unable to locate renderer executable. "
            "Please set the correct path in "
            "Edit -> Preferences -> Render\n"
        )
        return None, None
    rpath = enclose_rpath(rpath)

    cmd = prefix + rpath + " " + args + " " + f'"{input_file}"'

    # Note: at the moment (08-20-2022), width, height, background are
    # not managed by osp

    return cmd, outfile_actual


def _render_mergelightgroups(json_result):
    """Merge light groups in render result (helper).

    Args:
        json_result -- result file in json format - in/out argument, will be
            modified by this function
    """
    world_children = json_result["world"]["children"]
    world_children.sort(key=lambda x: x["type"] == "LIGHTS")  # Lights last
    lights = []

    def remaining_lightgroups():
        try:
            child = world_children[-1]
        except IndexError:
            return False
        return child["type"] == "LIGHTS"

    while remaining_lightgroups():
        light = world_children.pop()
        lights += light["children"]
    lightsmanager_children = json_result["lightsManager"]["children"]
    lightsmanager_children.extend(lights)


def _render_keep1cam(scene_graph):
    """Keep only one camera (the last one) in the scene graph.

    Args:
        scene_graph -- the scene graph, in json format - in/out, will be
            modified by this function
    """
    world_children = scene_graph["world"]["children"]
    cameras = [
        c for c in reversed(world_children) if c.get("freecadtype") == "camera"
    ]
    for index, cam in enumerate(cameras):
        world_children.remove(cam)
        if index == 0:
            # If the camera is the 1st one (in reverse order),
            # reinsert in front
            world_children.insert(0, cam)
    # Nota: camera must be in front of world children, otherwise import
    # fails (ospray bug?)

    # Add camera index
    scene_graph["camera"] = {
        "cameraIdx": 1,
        "cameraToWorld": {
            "affine": [0.0, 0.0, 0.0],
            "linear": {
                "x": [1.0, 0.0, 0.0],
                "y": [0.0, 1.0, 0.0],
                "z": [0.0, 0.0, 1.0],
            },
        },
    }


def _new_object_file_path(basename, extension, **kwargs):
    """Compute a new file name for export.

    The computation takes into account the directory dedicated for object
    files, that must be in keyword arguments.

    Returns:
        The new file name, and the relative path from project directory.
    """
    filename = f"{basename}.{extension}"
    project_directory = kwargs["project_directory"]
    object_directory = kwargs["object_directory"]
    abspath = os.path.join(object_directory, filename)
    relpath = os.path.relpath(abspath, project_directory)
    relpath = relpath.encode("unicode_escape").decode("utf-8")
    return abspath, relpath
