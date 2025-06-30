Materials - Advanced
====================

## How Render Workbench uses Material rendering settings

### Inputs
Once an object has been assigned a FreeCAD Material with relevant rendering
information, the rendering material computation process can take place at render
time.
It is based on the following inputs:
- An object being rendered
- A FreeCAD Material (https://Wiki.FreeCAD.Org/Material)
- A renderer
- A default color for the object being rendered. This data is taken from the
object's shape color in FreeCAD, and is provided to the process mainly for
fallback.

### Workflow
The workflow goes through the following steps:
1. The workbench looks into the FreeCAD Material for a passthrough material
definition for the given renderer.
A passthrough is a piece of code, written in the renderer's SDL (Scene
Description Language), which can be passed directly to the renderer.
2. If no passthrough, the workbench looks into the FreeCAD Material for a
standard rendering material definition.
This standard material is parsed and consolidated into an internal object,
which in turn is passed to the renderer plugin to be translated into
renderer's SDL (it being agreed that every renderer plugin is required to
have capabilities to translate standard materials into its renderer's SDL).
3. If no standard material, the workbench looks into FreeCAD Material for a
Father material. If there is one, it loops to step #1 with this Father.
4. If no father, the workbench tries to tinker a substitute fallback matte
material with FreeCAD Material DiffuseColor, or with object's default color,
or, at the last end, with white color.

Please note that the preferred method for material definition should definitely
be standard material, as it is the most generic way to do so.
Indeed, passthrough is a highly renderer-specific way to define a material, and
should be used only when standard material is not sufficient.

## Writing Material card for rendering <a name="parameters"></a>
In [Step #1](#step-1-create-a-material-in-your-document) above, you have imported a
Material Card into a Material, and then set up the rendering parameters.

If you don't want to specify your rendering parameters each time you create a
new Material in your document, you can also directly set your rendering
parameters in the Material Card.
A description of the FreeCAD material card format, the creation and the import
processes of such a card can be found here in FreeCAD documentation:
[FreeCAD material card file format](https://Wiki.FreeCAD.Org/Material#The_FreeCAD_material_card_file_format).

The relevant parameters to be used for rendering material are to be found
below in chapter [Material card settings for rendering](#parameters)

This section explains how to write rendering parameters in material cards files
(.FCMat).

### General recommendations

- Material card files (.FCMat) follows the "Ini" file format, as described in
FreeCAD documentation:
[FreeCAD material card file format](https://Wiki.FreeCAD.Org/Material#The_FreeCAD_material_card_file_format).
Be sure to have understood the general format before adding specific rendering
parameters.
- Rendering parameters should be gathered under a `[Rendering]` section.
It is not mandatory but it can improve the readability of the material
card.
- Decimal separator will always be a dot (`3.14`), whatever locale settings
may exist in the system.
- No quote must be used to enclose values, even string values. Such quotes would be
considered as part of the value by parser, and lead to subtle issues.
In particular, be careful when specifying `Render.Type` parameter:
  - `Render.Type=Diffuse` --> OK ;
  - `Render.Type="Diffuse"` --> NOK.
- Multi-line value are not allowed by FCMat syntax. Therefore all values
must fit in one line.
- Keys are case-sensitive: `Render.Type` is different from `Render.type`
- Values are case-sensitive as well: `Diffuse` is different from `diffuse`
- Duplicated keys lead to undefined behaviour.

### Standard materials

Standard materials are declared by specifying a type with a `Render.Type`
parameter, and setting some other parameters specific to this type.

#### Common parameters

All materials will accept the following input parameters:

Parameter | Type | Default value | Description
--------- | ---- | ------------- | -----------
`Render.<material>.Bump` | texonly |  | Bump texture
`Render.<material>.Normal` | texonly |  | Normal texture

Those parameters create bump/normal effects and are "texture only".

Nearly all materials, except `Substance_PBR`, will also accept the following,
for displacement effect:

Parameter | Type | Default value | Description
--------- | ---- | ------------- | -----------
`Render.<material>.Displacement` | texonly |  | Displacement texture


#### **Diffuse** Material

A simple matte material, usually based on ideal Lambertian reflection.

`Render.Type=Diffuse`

Parameter | Type | Default value | Description
--------- | ---- | ------------- | -----------
`Render.Diffuse.Color` | RGB | (0.8, 0.8, 0.8) | Diffuse color


#### **Disney** Material

A versatile material, based on the Disney principled model also known as the
"PBR" shader, capable of producing a wide variety of materials (e.g., plastic,
metal...) by combining multiple different layers and lobes.

`Render.Type=Disney`

Parameter | Type | Default value | Description
--------- | ---- | ------------- | -----------
`Render.Disney.BaseColor` | RGB | (0.8, 0.8, 0.8) | Base color
`Render.Disney.Subsurface` | float | 0.0 | Subsurface coefficient
`Render.Disney.Metallic` | float | 0.0 | Metallic coefficient
`Render.Disney.Specular` | float | 0.0 | Specular coefficient
`Render.Disney.SpecularTint` | float | 0.0 | Specular tint coefficient
`Render.Disney.Roughness` | float | 0.0 | Roughness coefficient
`Render.Disney.Anisotropic` | float | 0.0 | Anisotropic coefficient
`Render.Disney.Sheen` | float | 0.0 | Sheen coefficient
`Render.Disney.SheenTint` | float | 0.0 | Sheen tint coefficient
`Render.Disney.ClearCoat` | float | 0.0 | Clear coat coefficient
`Render.Disney.ClearCoatGloss` | float | 0.0 | Clear coat gloss coefficient

#### **Glass** Material

A glass-like shader mixing refraction and reflection at grazing angles,
suitable for transparent materials (glass, water, transparent plastics...).

`Render.Type=Glass`

Parameter | Type | Default value | Description
--------- | ---- | ------------- | -----------
`Render.Glass.IOR` | float | 1.5 | Index of refraction
`Render.Glass.Color` | RGB | (1, 1, 1) | Transmitted color

#### **Substance_PBR** Material

A shader created to give a good visual match with PBR materials (roughness
based workflow), specially intended to textured materials.

`Render.Type=Substance_PBR`

Parameter | Type | Default value | Description
--------- | ---- | ------------- | -----------
`Render.Substance_PBR.BaseColor` | RGB | (0.8, 0.8, 0.8) | Base color
`Render.Substance_PBR.Roughness` | float | 0.0 | Roughness
`Render.Substance_PBR.Metallic` | float | 0.0 | Metallic

#### **Mixed** Material

A material mixing a Diffuse and a Glass submaterials. This material is
specifically designed to render FreeCAD transparent objects.

`Render.Type=Mixed`

Parameter | Type | Default value | Description
--------- | ---- | ------------- | -----------
`Render.Mixed.Glass.IOR` | float | 1.5 | Index of refraction
`Render.Mixed.Glass.Color` | RGB | (1, 1, 1) | Transmitted color
`Render.Mixed.Diffuse.Color` | RGB | (0.8, 0.8, 0.8) | Diffuse color
`Render.Mixed.Transparency` | float | 0.5 | Mix ratio between Glass and Diffuse (should stay in [0,1], other values may lead to undefined behaviour)


#### Textures

Textures can be added in material card in order to be used by the material.

##### Texture Definition
A texture can be defined using the following parameters:

Parameter | Type | Default value | Description
--------- | ---- | ------------- | -----------
`Render.Textures.<name>.Images.<index>` | string | | Path to image
`Render.Textures.<name>.Scale` | float | | Scale to be applied to texture
`Render.Textures.<name>.Rotation` | float | | Rotation to be applied to texture
`Render.Textures.<name>.TranslationU` | float | | Translation to be applied to texture (U axis)
`Render.Textures.<name>.TranslationV` | float | | Translation to be applied to texture (V axis)

where:
- `<name>` is the name you give to the texture
- `<index>` is the index (unsigned integer) of the image, given that you can
  add as many images as you want. An important rule however: you must declare
  at least one image per texture and this image must have index = 0.

The path to image can (should) be relative. In this case, the base directory is
the one where the material card file is located.


##### Texture Reference

Once a texture has been defined, the syntax to reference it in a parameter is:

`<parameter> = Texture(<name>, <index>)`

where:
- `<parameter>` is the material parameter
- `<name>` is the texture name (as a string, double-quote enclosed)
- `<index>` is the index of the image to use (unsigned integer)

For instance:

`Render.Disney.BaseColor = Texture("Wood", 0)`

A default value can be added in case the renderer can't handle the texture.
This default value can be specified after a semi-colon. Example:

`Render.Disney.BaseColor = Texture("Wood", 0) ; (0.8, 0.8, 0.8)`


### **Passthrough** material

A material which allows to pass direct statements to the renderer. Warning:
the result is renderer-specific.

#### General syntax
Passthrough materials are defined using `Render.<renderer>.<line>` entries,
where:
* `<renderer>` is to be replaced by the name of the renderer targeted for the
passthrough
* `<line>` is to be replaced by line numbers, in a four-digits integer format:
`0001`, `0002` etc.

Note that spreading the material definition onto multiple keys/values is a
workaround to overcome the monoline syntactical limitation of FCMat format.

#### Renderer
For the passthrough material to be recognised internally, the renderer name
(`<renderer>`) must match the name of an existing renderer.
In particular, this name is case-sensitive.
Known renderers can be retrieved from Render workbench entering the following
code in FreeCAD console:
```python
import Render
print(Render.RENDERERS)
```

#### Lines order
Lines will be internally considered in sorted order, whatever order they follow
in FCMat file. For instance, the following sequence in FCMat file:
```
Render.Some_renderer.0002 = foo
Render.Some_renderer.0003 = baz
Render.Some_renderer.0001 = bar
```
...will always lead to the following internal representation:
```txt
bar
foo
baz
```

#### Pseudovariables
In addition, passthrough parameters syntax provides a set of pseudovariables
instantiated at render time, which can be useful to adapt the passthrough
to realtime context.

Those pseudovariables are described in the array below, note that the term
*rendered object* stands for the object which the material is applied to
at render time:

| Pseudovariable | Type   | Description                                                |
| -------------- | ------ | ---------------------------------------------------------- |
| `%NAME%`       | string | The name of the rendered object                            |
| `%RED%`        | float  | The default color of the rendered object - red component   |
| `%GREEN%`      | float  | The default color of the rendered object - green component |
| `%BLUE%`       | float  | The default color of the rendered object - blue component  |



### Material Cards Examples

#### Example #1: Diffuse material with red color
```INI
[Rendering]
Render.Type = Diffuse
Render.Diffuse.Color = (0.8,0,0)
```

#### Example #2: Glass material
```INI
[Rendering]
Render.Type = Glass
Render.Glass.IOR = 1.5
Render.Glass.Color = (1,1,1)
```

#### Example #3: Mirror passthrough material for Luxcore
```INI
[Rendering]
Render.Luxcore.0001 = scene.materials.%NAME%.type = mirror
Render.Luxcore.0002 = scene.materials.%NAME%.kr = %RED% %GREEN% %BLUE%
```

#### Example #4: Mirror passthrough material for Appleseed
```INI
[Rendering]
Render.Appleseed.0001 = <!-- Generated by FreeCAD - Color '%NAME%_color' -->
Render.Appleseed.0002 = <color name="%NAME%_color">
Render.Appleseed.0003 =     <parameter name="color_space" value="linear_rgb" />
Render.Appleseed.0004 =     <parameter name="multiplier" value="1.0" />
Render.Appleseed.0005 =     <parameter name="wavelength_range" value="400.0 700.0" />
Render.Appleseed.0006 =     <values> %RED% %GREEN% %BLUE% </values>
Render.Appleseed.0007 = </color>
Render.Appleseed.0008 = <bsdf name="%NAME%_bsdf" model="specular_brdf">
Render.Appleseed.0009 =     <parameter name="reflectance" value="%NAME%_color" />
Render.Appleseed.0010 = </bsdf>
Render.Appleseed.0011 = <material name="%NAME%" model="generic_material">
Render.Appleseed.0012 =     <parameter name="bsdf" value="%NAME%_bsdf" />
Render.Appleseed.0013 =     <parameter name="bump_amplitude" value="1.0" />
Render.Appleseed.0014 =     <parameter name="bump_offset" value="2.0" />
Render.Appleseed.0015 =     <parameter name="displacement_method" value="bump" />
Render.Appleseed.0016 =     <parameter name="normal_map_up" value="z" />
Render.Appleseed.0017 =     <parameter name="shade_alpha_cutouts" value="false" />
Render.Appleseed.0018 = </material>
```

#### Example #5: Textured Material
```INI
[Rendering]
Render.Type = Disney
Render.Disney.BaseColor = Texture("Wood", 0) ; (0.8,0.8,0.8)
Render.Disney.Subsurface = 0
Render.Disney.Metallic = 0
Render.Disney.Specular = 0.5
Render.Disney.SpecularTint = 0
Render.Disney.Roughness = Texture("Wood", 1);1
Render.Disney.Anisotropic = 0
Render.Disney.Sheen = 0
Render.Disney.SheenTint = 0
Render.Disney.ClearCoat = 0
Render.Disney.ClearCoatGloss = 0
Render.Disney.ClearCoatGloss = 0
Render.Disney.Normal = Texture("Wood", 2)
Render.Disney.Bump = Texture("Wood", 3)
Render.Textures.Wood.Images.0 = TexturedWood/Wood068_2K_Color.jpg
Render.Textures.Wood.Images.1 = TexturedWood/Wood068_2K_Roughness.jpg
Render.Textures.Wood.Images.2 = TexturedWood/Wood068_2K_NormalGL.jpg
Render.Textures.Wood.Images.3 = TexturedWood/Wood068_2K_Displacement.jpg
Render.Textures.Wood.Scale = 0.33
```
(provided that the sub-folder 'TexturedWood' contains the required image files)
