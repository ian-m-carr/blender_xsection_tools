import bpy
from typing import IO
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy_types import Operator
from mathutils import Vector

# conversion factor from meters to feet (ACF file is in ft!)
CONV_M_TO_FT = 3.28084


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

    def global_location_in_local_orientation(self, obj: bpy.types.Object) -> Vector:
        # global position
        glob_location = obj.matrix_world.translation.copy()
        # local rotation
        loc_rot = obj.matrix_local.to_euler()
        # rotate to local axes
        glob_location.rotate(loc_rot)

        return glob_location

    def write_station_element(self, o_file: IO, station_indx: int, station_z: float, point_indx: int, x: float, y: float):
        body_num = 0
        # X scaled by file scaling and converted m->ft
        x = x * CONV_M_TO_FT
        print('P _body/{}/_geo_xyz/{},{},0 {}'.format(body_num, station_indx, point_indx, round(x, 4)), file=o_file)
        # Y
        y = y * CONV_M_TO_FT
        print('P _body/{}/_geo_xyz/{},{},1 {}'.format(body_num, station_indx, point_indx, round(y, 4)), file=o_file)
        # Z
        print('P _body/{}/_geo_xyz/{},{},2 {}'.format(body_num, station_indx, point_indx, round(station_z * CONV_M_TO_FT, 4)), file=o_file)

    def write_station_data(self, o_file: IO, curve: bpy.types.Object, zero_z_pos: float, station_indx: int):
        # get the relative z position for the curve
        glob_pos = self.global_location_in_local_orientation(curve);
        station_z = glob_pos.z - zero_z_pos

        # points are reflected in X so for 8 intersections we have 16 points 0-15
        bez_points = [bez_point for spline in curve.data.splines for bez_point in spline.bezier_points]
        num_points = len(bez_points)

        for point_indx in range(num_points):
            # position 0 -> (n/2-1)
            coord = bez_points[point_indx].co

            self.write_station_element(o_file, station_indx, station_z, point_indx, coord.x, coord.y)
            # reflected in x (n-1) -> n/2
            self.write_station_element(o_file, station_indx, station_z, (num_points * 2) - 1 - point_indx, -(coord.x), coord.y)

        # now add the blank entries from numpoints to 18
        for i in range(num_points * 2, 18):
            self.write_station_element(o_file, station_indx, station_z, i, 0, 0)

        pass

    def write_blank_station_data(self, o_file: IO, first_station_indx: int, count: int):
        for station_indx in range(first_station_indx, first_station_indx+count):
            for n in range(18):
                self.write_station_element(o_file, station_indx, 0.0, n, 0.0, 0.0)

    def write_data(self, context):
        # selection should be a set of curves
        if len(context.selected_objects) == 0:
            self.report({'ERROR'}, 'No objects selected')
            return {"CANCELLED"}

        if not all([o.type == 'CURVE' for o in context.selected_objects]):
            self.report({'ERROR'}, 'Selection should contain only curves')
            return {"CANCELLED"}

        if not all([spline.type == 'BEZIER' for obj in context.selected_objects for spline in obj.data.splines]):
            self.report({'ERROR'}, 'Selection should contain only curves whose splines are all of type Bezier')
            return {"CANCELLED"}

        if any([spline.use_cyclic_u for obj in context.selected_objects for spline in obj.data.splines]):
            self.report({'WARNING'}, 'Unexpected cyclic curve detected, export function is expecting half section curves!')

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

        # sort the curves into z order (taking the local z axis) the greatest z marks the 0 position (front
        sorted_curve_objects = sorted(context.selected_objects, key=lambda obj: self.global_location_in_local_orientation(obj).z)

        # now take the zero position
        zero_z_pos = self.global_location_in_local_orientation(sorted_curve_objects[0]).z

        with open(self.filepath, 'w', encoding='utf-8') as f:
            for curve in sorted_curve_objects:
                self.write_station_data(f, curve, zero_z_pos, sorted_curve_objects.index(curve))

            # fill the blank elements up to curve 20
            last_index = len(sorted_curve_objects)
            self.write_blank_station_data(f, last_index, 20-last_index)


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
