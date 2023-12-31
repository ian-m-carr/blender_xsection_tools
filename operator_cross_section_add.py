import math
from typing import List

import bmesh
import bpy
import idprop
import mathutils
from bpy.props import (
    IntProperty, BoolProperty
)
from bpy_extras.object_utils import (
    AddObjectHelper
)
from bpy_types import (
    Panel
)
from mathutils import (
    Vector, Quaternion
)
from mathutils.geometry import (
    intersect_line_plane, intersect_line_line_2d
)


def bound_box(mesh_objs: List[bpy.types.Object]):
    corn0X = []
    corn0Y = []
    corn0Z = []
    corn6X = []
    corn6Y = []
    corn6Z = []

    for ob in mesh_objs:
        bbox_corners = [ob.matrix_world @ Vector(corner) for corner in ob.bound_box]
        corn0X.append(bbox_corners[0].x)
        corn0Y.append(bbox_corners[0].y)
        corn0Z.append(bbox_corners[0].z)
        corn6X.append(bbox_corners[6].x)
        corn6Y.append(bbox_corners[6].y)
        corn6Z.append(bbox_corners[6].z)

    minA = Vector((min(corn0X), min(corn0Y), min(corn0Z)))
    maxB = Vector((max(corn6X), max(corn6Y), max(corn6Z)))

    center_point = Vector(((minA.x + maxB.x) / 2, (minA.y + maxB.y) / 2, (minA.z + maxB.z) / 2))
    dimensions = Vector((maxB.x - minA.x, maxB.y - minA.y, maxB.z - minA.z))

    return center_point, dimensions


def sample_sections(section_objects: List[bpy.types.Object], sample_angles: List[float], outer_surface: bool = True) -> list[Vector]:
    '''
    Sample a set of sections (expected to be related co-planar edge sets representing cross sections of all objects in the same plane
    The sample derived should contain a set of samples on the the outermost surface represented by the section set
    '''

    # find the center and dimension of the bounding box of the object set (world coords)
    bbox_center, dim = bound_box(section_objects)

    # generate the fan coordinates

    # the set of n points in x,y distributed at sweep angle from each other,
    # the sampling lines are from center to each point
    line_end_points = []
    # print(sample_angles)
    for angle in sample_angles:
        q = Quaternion((0.0, 0.0, -1.0), math.radians(angle))
        v = Vector((0, max(dim.x, dim.y) * 2, 0))
        v.rotate(q)
        line_end_points.append(v)

    intersections = [None] * len(line_end_points)
    # iterate the sections and the edges in them
    for section_object in section_objects:
        if section_object.type == 'MESH':
            # create the bmesh container
            bm = bmesh.new()
            # populate from the section
            bm.from_mesh(section_object.data)

            for i in range(len(line_end_points)):
                end_point = line_end_points[i]
                for edge in bm.edges:
                    # does the line from the end point to the center intersect with the edge?
                    isect = intersect_line_line_2d(edge.verts[0].co, edge.verts[1].co, bbox_center + end_point, bbox_center)
                    if isect:
                        # is this the outermost intersection seen at this radial?
                        if intersections[i]:
                            exist_distance = (bbox_center + intersections[i]).length
                            new_distance = (bbox_center + Vector((isect.x, isect.y, 0))).length

                            # are we looking for the outer or the inner surface?
                            if (outer_surface and new_distance > exist_distance) or (not outer_surface and new_distance < exist_distance):
                                intersections[i] = (Vector((isect.x, isect.y, 0)))
                        else:
                            intersections[i] = (Vector((isect.x, isect.y, 0)))

            # free the bmesh storage
            bm.free()

    # return the not None outer edge points
    # cleanup any samples for radii where no intersection was found
    return [intersection for intersection in intersections if intersection]


def generate_sections(me, plane_co, plane_no):
    verts = []

    ed_xsect = {}
    for ed in me.edges:
        co1 = ed.verts[0].co
        co2 = ed.verts[1].co

        isect = intersect_line_plane(co1, co2, plane_co, plane_no)
        if isect != None:
            v1 = co2 - co1
            m1 = v1.magnitude
            v1.normalize()
            v2 = isect - co1
            m2 = v2.magnitude
            v2.normalize()

            # we know it should be co-linear so the dot product tells us
            # forward along the line 1.0 backward before the start point -1.0 or at 0.0
            d = v1.dot(v2)

            # same direction and within the limits of the line
            if d > 0.99 and m2 <= m1:
                # print('using: isect {}, dot {}, mag1 {}, mag2 {}'.format(isect, d, m1, m2))
                if isect in verts:
                    ed_xsect[ed.index] = verts.index(isect)
                else:
                    ed_xsect[ed.index] = len(verts)
                    verts.append(isect)
            elif abs(d) < 1e-5:
                # intersection is coincident with the start point (d = 0ish)
                # print('START: co1 {}, co2 {}, isect {}, dot {}, mag1 {}, mag2 {}'.format(co1, co2, isect, d, m1, m2))
                if isect in verts:
                    ed_xsect[ed.index] = verts.index(isect)
                else:
                    ed_xsect[ed.index] = len(verts)
                    verts.append(isect)
                    # else:
            #    print('MISS: co1 {}, co2 {}, isect {}, dot {}, mag1 {}, mag2 {}'.format(co1, co2, isect, d, m1, m2))

    edges = []
    for f in me.faces:
        edge_indices = [edge.index for edge in f.edges]
        # print('keys: {}'.format(edge_indices))

        # get the intersecting points if any.
        points = []
        for edge_index in edge_indices:
            # print('edge_index: {}'.format(edge_index))
            if edge_index in ed_xsect:
                isect = ed_xsect[edge_index]
                # don't add the same point more than once (corner intersections!)
                if not isect in points:
                    # print('match: {}'.format(edge_index))
                    points.append(isect)

        if len(points) == 2:
            edge = tuple(points)
            # don't add the same edge more than once
            if not edge in edges:
                edges.append(tuple(points))
                # print('appending: {}'.format(tuple(points)))
        # elif len(points) >= 2:
        #    print('oops {}, {}'.format(len(points), points))

    # print(edges)
    return verts, edges


class VIEW3D_PT_AddSectionsUI(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Cross Section Tools"
    bl_context = "objectmode"
    bl_category = 'Item'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        obj = context.object

        obj_name = obj.name if obj != None else ''
        if obj is not None:
            name = obj.name
        row = layout.row()
        row.label(text="Active object is: ", icon='OBJECT_DATA')
        box = layout.box()
        box.label(text=obj_name, icon='EDITMODE_HLT')

        col = layout.column()
        col.label(text="Generate cross sections:")

        col = layout.column(align=False)
        col.operator("mesh.cross_section_add", text="Generate")


class OBJECT_OT_AddSections(bpy.types.Operator, AddObjectHelper):
    """Add a cross section"""
    bl_idname = "mesh.cross_section_add"
    bl_label = "Add cross-section"
    bl_options = {'REGISTER', 'UNDO'}

    generate_meshes: BoolProperty(
        name="Generate Meshes",
        description="Should we generate (and keep) a cross section Mesh for each object in the selection",
        default=False
    )
    generate_curve: BoolProperty(
        name="Generate Curve",
        description="Should we generate a sampled curve for the inner or outer surface of the section",
        default=True
    )
    outer_surface: BoolProperty(
        name="Outer Surface",
        description="Detect the outer surface (true) or inner surface (false)",
        default=True
    )
    half_section_sampling: BoolProperty(
        name="Sample Half Section",
        description="Curve will be generated over the half section (+ve Y)",
        default=True
    )
    num_samples: IntProperty(
        name="Number samples",
        description="The number of sampling radials used to generate the curve (per half)",
        default=9,
        max=20
    )
    save_sample_angles: BoolProperty(
        name="Save sampling angles",
        description="Save the angles used for sampling to the target object for re-use/adjustment",
        default=False
    )
    generate_bezier: BoolProperty(
        name="Generate bezier curve",
        description="Generate the curve as a Bezier curve, alternative is a polyline",
        default=False
    )

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        layout.prop(self, "generate_meshes")
        layout.prop(self, "generate_curve")

        if self.generate_curve:
            box = layout.box()
            box.label(text='Curve config', icon='CURVE_DATA')
            box.prop(self, "generate_bezier")
            box.prop(self, "outer_surface")
            box.prop(self, "half_section_sampling")
            sample_angles_prop = context.active_object.get('sample_angles')
            if sample_angles_prop != None:
                box.label(text="found sampling angles property, num-samples: {}".format(len(sample_angles_prop) + 2))
            else:
                box.prop(self, "num_samples")
            box.prop(self, "save_sample_angles")

    @classmethod
    def poll(cls, context):
        # need at least 2 objects selected and 1 active
        return context.active_object is not None and len(context.selected_objects) > 1

    def generate_curve_from_points(self, context, plane_location: Vector, points: list[Vector], z_adjust: float, body_id: int):
        # create the Curve Datablock
        curve_data = bpy.data.curves.new('myCurve', type='CURVE')

        # map coords to spline
        if self.generate_bezier:
            polyline = curve_data.splines.new('BEZIER')
        else:
            polyline = curve_data.splines.new('POLY')

        # if we are sampling 360 the resultant spline should be cyclic!
        polyline.use_cyclic_u = not self.half_section_sampling

        if self.generate_bezier:
            polyline.bezier_points.add(len(points) - 1)
            for i, coord in enumerate(points):
                polyline.bezier_points[i].co = points[i]
                polyline.bezier_points[i].handle_left_type = 'AUTO'
                polyline.bezier_points[i].handle_right_type = 'AUTO'
        else:
            polyline.points.add(len(points) - 1)
            for i, coord in enumerate(points):
                polyline.points[i].co = points[i].to_4d()

        # create Object
        curve_obj = bpy.data.objects.new('myCurve', curve_data)
        # Place at origin of the cutting plane
        curve_obj.location = plane_location  # context.active_object.location
        curve_obj.rotation_euler = context.active_object.rotation_euler

        # record the offset in z if we have one
        if z_adjust != 0.0:
            curve_obj['z_adjust'] = z_adjust

        if body_id != 0:
            curve_obj['body_id'] = body_id

        # attach to scene
        context.view_layer.active_layer_collection.collection.objects.link(curve_obj)

    def generate_section(self, context, z_offset: float, z_adjust: float, body_id: int):
        # take the z axis from the active object
        plane_location = context.active_object.location.copy()
        plane_z = Vector((0, 0, -1))
        plane_z.rotate(context.active_object.matrix_world.to_euler())

        plane_location = plane_location + plane_z * z_offset

        meshes = []
        for target_object in context.selected_objects:
            if target_object != context.active_object and target_object.type == 'MESH':
                bm = bmesh.new()
                bm.from_mesh(target_object.data)

                # make sure the mesh is baked to the object transforms
                # apply transforms equivalent
                bm.transform(target_object.matrix_world)

                verts, edge_indices = generate_sections(bm, plane_location, plane_z)

                if len(edge_indices) > 0:
                    mesh = bpy.data.meshes.new("Section")

                    bm = bmesh.new()

                    for v_co in verts:
                        bm.verts.new(v_co)

                    bm.verts.ensure_lookup_table()

                    for edge_idx in edge_indices:
                        bm.edges.new([bm.verts[i] for i in edge_idx])

                    mat_offset = mathutils.Matrix.Translation(Vector((0, 0, z_offset)))
                    bm.transform(mat_offset @ context.active_object.matrix_world.inverted())
                    bm.to_mesh(mesh)
                    # free the mesh storage
                    bm.free()
                    mesh.update()
                    meshes.append(mesh)

        if len(meshes) == 0:
            self.report({'WARNING'}, f'No cross sections generated at offset {z_offset}')

            # add an empty (0,0,0) curve at the sampling point!
            if self.generate_curve:
                sample_angles_prop = target_object.get('sample_angles')
                point_count = self.num_samples
                if sample_angles_prop:
                    point_count = len(sample_angles_prop)

                points = [Vector((0,0,0))] * point_count
                self.generate_curve_from_points(context, plane_location, points, z_adjust, body_id)

        else:
            section_objects = []
            for mesh in meshes:
                # Create new object with our datablock.
                section_object = bpy.data.objects.new(name="Section", object_data=mesh)

                # Place at origin of the cutting plane
                section_object.location = plane_location  # context.active_object.location
                section_object.rotation_euler = context.active_object.rotation_euler

                # append to the section collection
                section_objects.append(section_object)

            # are we generating the surface curve?
            if self.generate_curve:
                # do we have a predetermined set of sample angles?
                sample_angles_prop = target_object.get('sample_angles')
                if sample_angles_prop == None:
                    sweep_angle_step = 180 / (self.num_samples - 1)
                    # generate the angles
                    sample_angles = [i * sweep_angle_step for i in range(self.num_samples)]
                else:
                    # add the begining and end angles
                    sample_angles = sample_angles_prop.to_list()
                    sample_angles.insert(0, 0)
                    sample_angles.append(180)

                if len(sample_angles) < 3:
                    self.report({'ERROR'}, "insufficient sampling angles supplied! {}".format(len(sample_angles)))
                if len(sample_angles) != self.num_samples:
                    self.report({'ERROR'},
                                "supplied sample angle count mismatch, for {} samples expected {} angles, don't supply 0 and 180".format(self.num_samples,
                                                                                                                                         len(sample_angles)))
                    return

                # should we write the angles back to target object to allow the user to edit and re-use?
                if self.save_sample_angles:
                    saved_angles = sample_angles.copy()
                    # loose the first and last
                    saved_angles.pop(len(sample_angles) - 1)
                    saved_angles.pop(0)

                    target_object['sample_angles'] = saved_angles

                # if we are not half sectioning then reflect the sampling angles
                if not self.half_section_sampling:
                    for i in range(len(sample_angles) - 2, 0, -1):
                        sample_angles.append(-sample_angles[i])

                points = sample_sections(section_objects, sample_angles, self.outer_surface)

                # print('points {}'.format(points))

                self.generate_curve_from_points(context, plane_location, points, z_adjust, body_id)

            # delete or preserve the section meshes
            for section_object in section_objects:
                # are we preserving the mesh objects?
                if self.generate_meshes:
                    # Link the object to the active collection of current view layer,
                    # so that it'll appear in the current scene.
                    context.view_layer.active_layer_collection.collection.objects.link(section_object)
                else:
                    # remove it
                    bpy.data.objects.remove(section_object, do_unlink=True)

    def execute(self, context):
        if context.active_object == None:
            self.report({'INFO'}, 'No active object selected')
            return {'FINISHED'}

        sample_offsets = [0.0]
        z_offset_prop = context.active_object.get('z_samples')
        if z_offset_prop != None:
            if type(z_offset_prop) is idprop.types.IDPropertyArray:
                sample_offsets = z_offset_prop.to_list()
            else:
                sample_offsets = [z_offset_prop]

        z_adjust = 0.0
        z_adjust_prop = context.active_object.get('z_adjust')
        if z_adjust_prop != None:
            z_adjust = z_adjust_prop

        body_id = 0
        body_id_prop = context.active_object.get('body_id')
        if body_id_prop != None:
            body_id = body_id_prop

        for offset in sample_offsets:
            self.generate_section(context, offset, z_adjust, body_id)

        return {'FINISHED'}


def menu_func(self, context):
    self.layout.operator(OBJECT_OT_AddSections.bl_idname, icon='MESH_CUBE')


# Class List
classes = (
    VIEW3D_PT_AddSectionsUI,
    OBJECT_OT_AddSections
)


# Register all operators and panels
def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
