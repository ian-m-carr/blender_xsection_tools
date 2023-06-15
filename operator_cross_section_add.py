import bpy
import bmesh

from bpy_extras import object_utils
from bpy_extras.object_utils import (
    AddObjectHelper
)
from bpy.types import (
    Operator,
    Panel,
    AddonPreferences
)
from bpy.props import (
    FloatProperty, IntProperty, FloatVectorProperty
)
from mathutils import (
    Vector,
    Matrix
)
from mathutils.geometry import (
    intersect_line_plane
)


def generate_sections(me, count, step_size, plane_co, plane_no):
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
        elif len(points) >= 2:
            print('oops {}, {}'.format(len(points), points))


    print(edges)
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

    num_sections: IntProperty(
        name="Num Sections",
        description="The number of sections",
        min=1, soft_max=10, max=100,
        default=1,
    )
    step_size: FloatProperty(
        name="Step Size",
        description="Distance to step between sections",
        min=0.01, max=100.0,
        default=1.0,
    )

    @classmethod
    def poll(cls, context):
        # need at least 2 objects selected and 1 active
        return context.active_object is not None and len(context.selected_objects) > 1

    def execute(self, context):
        if context.active_object == None:
            self.report({'INFO'}, 'No active object selected')
            return {'FINISHED'}

        # set the location to the origin - used by the create object helper
        self.location = Vector((0, 0, 0))
        # self.rotation = context.active_object.matrix_world.to_euler()

        # take the z axis from the active object
        plane_location = context.active_object.location
        plane_z = Vector((0, 0, -1))
        plane_z.rotate(context.active_object.matrix_world.to_euler())

        meshes = []
        for target_object in context.selected_objects:
            if target_object != context.active_object and target_object.type == 'MESH':
                bm = bmesh.new()
                bm.from_mesh(target_object.data)

                # make sure the mesh is baked to the object transforms
                # apply transforms equivalent
                bm.transform(target_object.matrix_basis)

                verts, edge_indices = generate_sections(bm, self.num_sections, self.step_size, plane_location, plane_z)

                if len(edge_indices) > 0:
                    mesh = bpy.data.meshes.new("Section")

                    bm = bmesh.new()

                    for v_co in verts:
                        bm.verts.new(v_co)

                    bm.verts.ensure_lookup_table()

                    for edge_idx in edge_indices:
                        bm.edges.new([bm.verts[i] for i in edge_idx])

                    bm.to_mesh(mesh)
                    mesh.update()

                    meshes.append(mesh)

        if len(meshes) == 0:
            self.report({'INFO'}, 'No cross sections generated')
        else:
            for mesh in meshes:
                # add the mesh as an object into the scene with this utility module
                object_utils.object_data_add(context, mesh, operator=self)
                # bpy.ops.object.convert('CURVE')

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
