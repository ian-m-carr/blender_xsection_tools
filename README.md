Tooling to generate Mesh Cross-Sections projected onto a plane at a selected location.

Tooling appears in the Edit/Object mode UI under "Cross Section Tools"
And the X-Plane ACF body exporter appears in the export menu.

![Screenshot](documentation/screenshot_1.jpg)

To generate cross sections, a selection should contain at least two objects the active object is taken as the definition 
for the cutting plane on which the cross-section will be projected. The X/Y axis define the plane and the Z the normal.
For each of the other selected components, if they are meshes, a cross-section mesh object named "Section(.n)" is 
generated if the plane cuts any part of the selected object.

In addition there is an option to generate sampled curves from the inner or outer surfaces at each cross section, 
the number of sample points can be selected, and the curve can either be generated as a Bezier or a Polyline. 
The sampling works by 'ray tracing' from the center of the bounding box outward and taking the first (inner) or 
last (outer) intersection with the section meshes along each ray. This works for relatively simple shapes cylinders
basically things like an aircraft fuselage! Complex folded shapes an I-beam for instance will not surface detect
correctly, you can still generate the cross-sectional meshes but surface detection will be a manual process.

Finally the exporter option will write the data from a set of cross sections in an X-Plane 'Body' format into an export
file, the idea is that you can select the content of the file, cut and paste it into an actual ACF file to obtain the 
profile of the body. Select the set of surface curves and hit the export button!

The 'Generate' button will only activate if there are at least two selected items, and one of them is active. 
The Active object label will display the name of the object to be used as the cutting plane.

The second screenshot below shows a cross-section generated with the cutting plane rotated about the X axis

![Screenshot](documentation/screenshot_2.jpg)

The next shot shows a more complex model comprised of several objects and internal structure 
(an aircraft engine nacelle) The slicing plane is defined by the arrowed empty at the nose.

![Screenshot](documentation/screenshot_3.jpg)

In this case the empty carries a number of optional custom properties

![Screenshot](documentation/screenshot_4.jpg)

**z_samples:** The z_samples is a float array containing offset distances to generate a number of cross sections stepping back the 
z ordinate by the given amounts:

![Screenshot](documentation/screenshot_5.jpg)

**z_adjust**:By default the exporter will set the Z 0 position as the position of the highest Z in the samples. The z_adjust is 
basically used to modify the exported 0 position, in this case the X-Plane 'engine' location is a little to the right
of the spinner tip, so we add 43.3cm offset

**body_id**: The exporter will generate a body '0' by default, if this property is specified then the output data will 
contain an appropriately numbered body

The next screen shows the content of the 'redo' panel 

![Screenshot](documentation/screenshot_6.jpg)

The 'Generate Meshes' panel indicates whether the meshes remain in the model on completion (they are always generated
to be sampled but are only kept if this is checked)

The 'Generate Curve' option controls the sampling of the meshes into surface curves. If selected the Curve config options
willbe shown

The 'Generate bezier curve' option will use a 'Bezier' representation of the surface, if not selected then a 'Polyline'
will be produced instead (for X-Plane this is probably more appropriate)

The 'Outer surface' option selects the furthest from the center sample as the surface, unchecked the nearest to center
inner face will be sampled.

The 'sample Half section' option chooses to take a 0-180 set of samples, unchecked this will take 0-360 
(and importantly twice the number of samples selected below)

The 'Number of samples' option selects how many sample points are taken (0 and 180 are always present others are 
spaced between)

Save sample angles will write a float array custom property to the plane definition object 'sample_angles' with
the set of angles at which samples are taken, if this is present when generating the curves, the content will
override the default equally spaced sampling angles and can be used to sample at angles which better follow 
contours of the body being sampled.

The next shot shows the sampled curves for the nacelle

![Screenshot](documentation/screenshot_7.jpg)

And the next one shows the mesh cross sections generated. The front green one shows some internal structure and the 
rear white one s actually composed of two meshes from two separate components. Thes have been sampled in the previous 
shot to give the 'outer' surface curves shown

![Screenshot](documentation/screenshot_8.jpg)
