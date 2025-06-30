# Project options

Project options allow to control rendering process and result.

## Rendering process options

Parameter | Type | Description
----------|------|------------
`Renderer` | String | The name of the raytracing engine to use
`Template` | String | The template to be used by the rendering
`Delayed Build` | Boolean | If true, the views will be updated at render time only
`Page Result` | Included File | The exported file to be sent to the external renderer
`Output Image` | File | The image file saved by the rendering
`Open After Render` | Boolean | If true, the rendered image is opened in FreeCAD when the rendering is done

Comments:
* The Render workbench uses the same
  [template](https://Wiki.FreeCAD.Org/Raytracing_Workbench#Templates)
  logic as the Raytracing workbench, and templates are fully compatible.
  Templates usually contain:
  - Lighting presets
  - Renderer specific options (resolution, sampler, thread counts, GPU use...)

  We provide a few default templates, but you can write and use your own ones,
  if necessary.\
  Template file is defined by `Template` parameter. It contains the *relative*
  path to the template, starting from the workbench's templates subdirectory.
  The use of the relative path, instead of the absolute path, makes the FreeCAD
  file fully portable from one computer to another. By default, the `Template`
  parameter is read-only in the GUI: the recommended way to modify it is to use
  the context menu of the Project.

* Like the builtin Raytracing workbench, the Render workbench offers the
  possibility to update the View objects whenever its source object changes,
  which costs extra processing time every time the source object changes, but
  quickens the final export. However it also offers a mode where the views are
  updated all at once, only when the render is performed. This makes the render
  slower, but adds virtually no slowdown during the work with FreeCAD, no
  matter the size of a Render project. This behaviour is controlled by the `Delayed Build` parameter.

## Rendering result options

Parameter | Type | Description
----------|------|------------
`Render Width` | Integer | The width of the rendered image (in pixels)
`Render Height` | Integer | The height of the rendered image (in pixels)
`Ground Plane` | Boolean | If true, a default ground plane is added to the scene
`Ground Plane Z` | Float | Z position of ground plane
`Ground Plane Color` | RGB | Color of ground plane
`Ground Plane Size Factor` | Float | A factor to control the size of the ground plane. Default value 1.0 makes the ground plane fit the scene bounding box.
`Transparency Sensitivity` | Integer | A factor to augment transparency in whole scene. This affects only implicit materials (materials generated from shape color and transparency), it will have no effect on explicit materials (materials generated from material cards).

## Mesher options

These parameters controls mesher behaviour. Render uses FreeCAD standard
mesher, you may find some more information in [FreeCAD
documentation](https://Wiki.FreeCAD.Org/Mesh_FromPartShape#Standard_mesher)

Parameter | Type | Description
----------|------|------------
`Linear Deflection` | Float | The maximum linear deviation of a mesh section from the surface of the object (the lower the finer).
`Angular Deflection` | Float | The maximum angular deviation from one mesh section to the next, in radians. This setting is used when meshing curved surfaces (the lower the finer).

**Warning:** Be careful when setting those parameters. Unappropriate values can lead to extremely long processing duration.
