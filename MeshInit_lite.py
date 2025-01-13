bl_info = {
    "name": "Initialize Mesh UI",
    "blender": (4, 3, 0),  # Minimum Blender version
    "category": "Object",
    "author": "Dima",
    "version": (1, 0, 0),
    "description": "An add-on to initialize and process mesh objects.",
}

import bpy

class OBJECT_OT_InitializeMesh(bpy.types.Operator):
    """Do The Thing: Duplicate mesh, manage collections, and assign material."""
    bl_idname = "object.initialize_mesh"
    bl_label = "Do The Thing!"
    bl_options = {'REGISTER', 'UNDO'}

    object_name: bpy.props.StringProperty(name="Object Name", default="NewObject")

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "No active mesh object selected.")
            return {'CANCELLED'}

        # Duplicate the object
        duplicate = obj.copy()
        duplicate.data = obj.data.copy()
        context.collection.objects.link(duplicate)

        # Move the original to the _original collection and exclude it from the view layer
        original_collection = bpy.data.collections.get(f"{obj.name}_original")
        if not original_collection:
            original_collection = bpy.data.collections.new(name=f"{obj.name}_original")
            context.scene.collection.children.link(original_collection)
        original_collection.objects.link(obj)
        context.collection.objects.unlink(obj)

        view_layer = context.view_layer.layer_collection.children.get(original_collection.name)
        if view_layer:
            view_layer.exclude = True

        # Keep the original material on the original object
        original_materials = list(obj.data.materials)

        # Remove the old material from the duplicate if reset_material_toggle is active
        if context.scene.reset_material_toggle:
            duplicate.data.materials.clear()
            # Create and assign a new material to the duplicate
            mat = bpy.data.materials.new(name=self.object_name)
            mat.use_nodes = True
            duplicate.data.materials.append(mat)

        # Restore the original materials to the original object
        obj.data.materials.clear()
        for mat in original_materials:
            obj.data.materials.append(mat)

        # Move the duplicate to a new collection
        initialized_collection = bpy.data.collections.get(f"{self.object_name}_initialized")
        if not initialized_collection:
            initialized_collection = bpy.data.collections.new(name=f"{self.object_name}_initialized")
            context.scene.collection.children.link(initialized_collection)
        initialized_collection.objects.link(duplicate)
        context.collection.objects.unlink(duplicate)

        duplicate.name = self.object_name
        self.report({'INFO'}, f"Mesh initialized with name: {self.object_name}")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class OBJECT_PT_InitializeMeshPanel(bpy.types.Panel):
    """UI Panel for Initialize Mesh"""
    bl_label = "Mesh Tools"
    bl_idname = "OBJECT_PT_initialize_mesh_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Mesh Tools'

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.prop(scene, "reset_material_toggle")
        layout.prop(scene, "apply_scale_toggle")
        layout.prop(scene, "apply_rotation_toggle")

        layout.separator()
        layout.operator(OBJECT_OT_InitializeMesh.bl_idname)

# Add properties to scene for toggles
bpy.types.Scene.reset_material_toggle = bpy.props.BoolProperty(name="Reset Material", default=False)
bpy.types.Scene.apply_scale_toggle = bpy.props.BoolProperty(name="Apply Scale", default=True)
bpy.types.Scene.apply_rotation_toggle = bpy.props.BoolProperty(name="Apply Rotation", default=True)

classes = [
    OBJECT_OT_InitializeMesh,
    OBJECT_PT_InitializeMeshPanel
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.reset_material_toggle
    del bpy.types.Scene.apply_scale_toggle
    del bpy.types.Scene.apply_rotation_toggle

if __name__ == "__main__":
    register()
