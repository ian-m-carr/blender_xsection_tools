import bpy

# ExportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy_types import Operator


class ExportACFBodyData(Operator, ExportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "export_acf.body_data"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "X-Plane body profile export (.acf)"

    # ExportHelper mixin class uses this
    filename_ext = ".acf"

    filter_glob: StringProperty(
        default="*.acf",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    @classmethod
    def poll(cls, context):
        # need at least 1 objects selected and all selected objects should be curves
        return len(context.selected_objects) > 0 and all([o.type == 'CURVE' for o in context.selected_objects])

    def execute(self, context):
        return self.write_data(context)

    def write_data(self, context):
        # selection should be a set of curves
        if len(context.selected_objects) == 0:
            self.report({'ERROR'}, 'No objects selected')
            return {"CANCELLED"}

        if not all([o.type == 'CURVE' for o in context.selected_objects]):
            self.report({'ERROR'}, 'Selection should contain only curves')
            return {"CANCELLED"}

        if not all([spline.type == 'BEZIER' for obj in context.selected_objects for spline in obj.data.splines ]):
            self.report({'ERROR'}, 'Selection should contain only curves whose splines are all of type Bezier')
            return {"CANCELLED"}

        # the number of points in each curve should be the same and in the range 3-9
        count = -1
        for o in context.selected_objects:
            npoints = sum(len(spline.bezier_points) for spline in o.data.splines)

            if npoints == 0:
                self.report({'ERROR'}, 'At least one of the selected curves contains no points')
                return {"CANCELLED"}
            if count == -1:
                count = npoints
            elif count != npoints:
               self.report({'ERROR'}, 'All the curves should contain the same number of points!')
               return {"CANCELLED"}

        if count < 3 or count > 9:
            self.report({'ERROR'}, 'Expected point counts to be between 3 and 9 inclusive!')
            return {"CANCELLED"}

        # sort the curves into z order the greatest z marks the 0 position (front)
        sorted_curve_objects = sorted(context.selected_objects, key=lambda obj: obj.location.z)

        # now take the zero position
        zero_z_pos = sorted_curve_objects[0].location.z

        print("running write_some_data...")
        f = open(self.filepath, 'w', encoding='utf-8')
        # f.write("Hello World %s" % use_some_setting)
        f.close()

        return {'FINISHED'}


# Only needed if you want to add into a dynamic menu
def menu_func_export(self, context):
    self.layout.operator(ExportACFBodyData.bl_idname, text="X-Plane ACF Body export (.acf)")


# Register and add to the "file selector" menu (required to use F3 search "Text Export Operator" for quick access).
def register():
    bpy.utils.register_class(ExportACFBodyData)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(ExportACFBodyData)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()
