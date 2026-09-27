"""Read Blender extension registration API before task-only MPFB setup."""
import bpy,json
parameters=[]
for p in bpy.context.preferences.extensions.repos.bl_rna.functions['new'].parameters:
    parameters.append({'identifier':p.identifier,'type':p.type,'required':p.is_required})
print(json.dumps({'repo_new':parameters,'autosave_preferences':bpy.context.preferences.use_preferences_save}))
