import os
from pyfbsdk import *

"MotionBuilder script for batch rendering to silhouette images"
"from FBX models and BVH mocap data."

### SCRIPT CONFIGURATION
FBX_FOLDER = r'F:\silhouette\fbx'
BVH_FOLDER = r'F:\silhouette\bvh'
DST_FOLDER = r'F:\silhouette\out'

SHADER_PATH = r'E:\MoBuPy\silhouette.cgfx'
RENDER_FILE_FORMAT = '.jpg'
RESOLUTION_X = 385
RESOLUTION_Y = 450

FRAME_BEGINNING = 4
# FRAME_SPAN = 12  # not used
# IGNORE_EXISTING_FILE = True  # not implemented yet
### END OF SCRIPT CONFIGURATION

biped_map = [
    ('Reference', 'BVH:reference'),
    ('Hips', 'BVH:Hips'),
    ('LeftUpLeg', 'BVH:LeftUpLeg'),
    ('LeftLeg', 'BVH:LeftLeg'),
    ('LeftFoot', 'BVH:LeftFoot'),
    ('RightUpLeg', 'BVH:RightUpLeg'),
    ('RightLeg', 'BVH:RightLeg'),
    ('RightFoot', 'BVH:RightFoot'),
    ('Spine', 'BVH:Spine'),
    ('LeftArm', 'BVH:LeftArm'),
    ('LeftForeArm', 'BVH:LeftForeArm'),
    ('LeftHand', 'BVH:LeftHand'),
    ('RightArm', 'BVH:RightArm'),
    ('RightForeArm', 'BVH:RightForeArm'),
    ('RightHand', 'BVH:RightHand'),
    ('Head', 'BVH:Head'),
    ('Neck', 'BVH:Neck')]


# initializes global variables
system = FBSystem()
app = FBApplication()
current_character = None
player = FBPlayerControl()

## helper functions
def add_joint_to_character(character, slot, joint_name):
    joint = FBFindModelByName(joint_name)
    prop = character.PropertyList.Find(slot + 'Link')
    prop.append(joint)

def prepare_cleaning(objects_to_clean, node):
    objects_to_clean.append(node)
    for child in node.Children:
        prepare_cleaning(objects_to_clean, child)

def early_time(t1, t2):
    return t1.Get() < t2.Get() and t1 or t2

def set_camera(width, height):
    cam_sil = FBCamera('silhouette')
    cam_sil.ResolutionMode = FBCameraResolutionMode.kFBResolutionCustom
    cam_sil.ResolutionWidth = width
    cam_sil.ResolutionHeight = height
    cam_sil.ViewShowAxis = False
    cam_sil.ViewShowGrid = False
    cam_sil.BackGroundColor = FBColor(0, 0, 0)

    hips = FBFindModelByName('Hips')
    # Adds a position constraint (type index 5) to make camera follow
    # the character.
    pos_cons = FBConstraintManager().TypeCreateConstraint(5)
    system.Scene.Constraints.append(pos_cons)
    pos_cons.ReferenceAdd (0, cam_sil)  # constrainted
    pos_cons.ReferenceAdd (1, hips)  # constraint source

    pos_cons.Active = False  # temporarily disables constraint
    cam_sil.Interest = hips
    pos_cons.Snap()  # activates constraint

    render = system.Renderer
    render.CurrentCamera = cam_sil
    return pos_cons  # for further position controlling

def update_camera_pos(pos_constraint, fbpos):
    pos_constraint.PropertyList.Find('Translation').Data = fbpos

def reset_player(p):
    player.GotoStart()
    system.Scene.Evaluate()

def apply_shader():
    shader_manager = FBShaderManager()
    shader = shader_manager.CreateShader('CgfxShader')
    # sets Cgfx shader source
    shader.PropertyList.Find('Shader File Path').Data = SHADER_PATH
    for comp in system.Scene.Components:
        if comp.ClassName() == 'FBModel':
            # Chooses appropriate shading mode. (When we drag & drop shaders
            # into MoBu the application will automatically change it.)
            comp.ShadingMode = FBModelShadingMode.kFBModelShadingAll
            shader.ReplaceAll(comp)

def all_files(top, ext):
    file_list = []
    for root, dirs, files in os.walk(top):
        files = [os.path.join(root, f) for f in files if f.endswith(ext)]
        file_list.extend(files)
    return file_list

def get_dst_path(fbx_file, bvh_file, cam_id):
    """Gets the destination path of rendering images.

    FBX_FOLDER = r'A:\d0'; fbx_file = r'A:\d0\d1\d2\model.fbx'
    BVH_FOLDER = r'B:\d3'; bvh_file = r'B:\d3\04\04_08.bvh'
    cam_id = 2
    DST_FOLDER = r'C:\silhouette'
    RENDER_FILE_FORMAT = '.jpg'
    get_dst_path(fbx_file, bvh_file, cam_id) == \
        'C:\\silhouette\\d1\\d2\\model\\04\\04_08\\C2-.jpg'
    """
    bvh_base_no_ext = os.path.splitext(os.path.basename(bvh_file))[0]
    bvh_folder_rel = os.path.dirname(os.path.relpath(bvh_file, BVH_FOLDER))
    fbx_folder_rel = os.path.splitext(os.path.relpath(fbx_file, FBX_FOLDER))[0]
    dst_folder = os.path.join(DST_FOLDER, fbx_folder_rel, bvh_folder_rel, bvh_base_no_ext)

    if not os.path.exists(dst_folder):
        try:
            os.makedirs(dst_folder)
        except:
            # handles potential race condition here?
            pass

    dst_path = os.path.join(dst_folder, 'C' + str(cam_id) + '-' + RENDER_FILE_FORMAT)
    # if IGNORE_EXISTING_FILE and os.path.exists(dst_path):
    #     return
    return dst_path

def discard_frames(dst_path):
    # WORKAROUND: discards useless frames
    frames_to_discard = [FRAME_BEGINNING - 1, FRAME_BEGINNING - 2]
    if FRAME_BEGINNING == 0:
        frames_to_discard = frames_to_discard[:1]

    for frame_id in frames_to_discard:
        del_path = str.replace(dst_path, RENDER_FILE_FORMAT,
            '{0:04}'.format(frame_id) + RENDER_FILE_FORMAT)
        try:
            os.remove(del_path)
        except:
            pass


def calc_camera_pos(radius, y, n):
    from math import pi, sin, cos
    delta = pi * 2 / n
    return [FBVector3d(radius * sin(delta * i), y, radius * cos(delta * i))
        for i in range(n)]


##########################################

def process_fbx(fbx_file, bvh_list):
    print "Processing %s:" % fbx_file

    app.FileOpen(fbx_file)
    current_character = app.CurrentCharacter

    # hides the reference & root mark (a 3d-axis-like cross of red-green-blue colors)
    ref = FBFindModelByName('Reference')
    ref.Visibility = False
    root = FBFindModelByName('Root')
    root.Visibility = False

    player.SetTransportFps(FBTimeMode.kFBTimeModeCustom, 12)
    pos_constraint = set_camera(RESOLUTION_X, RESOLUTION_Y)
    apply_shader()

    ## Prepare rendering
    # Gets default rendering options saved in the FBX file.
    options = FBVideoGrabber().GetOptions()

    # sets VideoCodec options
    video_manager = FBVideoCodecManager()
    video_manager.VideoCodecMode = FBVideoCodecMode.FBVideoCodecUncompressed

    # WORKAROUND: Substracts start frame by 2 to prevent the second frame
    # of each movie (except the first one) from corrupting.
    #
    # NOTE: This issue is related to calling FBSystem.Scene.Evaluate()
    # although its actual cause still remains unknown.
    # time_start = FBTime(0, 0, 0,
    #     FRAME_BEGINNING - 1, 0, FBTimeMode.kFBTimeMode30Frames)
    # time_stop = FBTime(0, 0, 0,
    #     FRAME_BEGINNING + FRAME_SPAN + 2, 0, FBTimeMode.kFBTimeMode30Frames)

    options.BitsPerPixel = FBVideoRenderDepth().FBVideoRender24Bits


    def process_bvh(bvh_file):
        print "\tRetargetting %s:" % bvh_file

        # Goes to Frame 0 to put the character stand in T-pose
        # before retargetting.
        reset_player(player)

        app.FileImport(bvh_file)
        new_character = FBCharacter('ImportedCharacter')
        for char_slot, bvh_joint in biped_map:
            add_joint_to_character(new_character, char_slot, bvh_joint)

        new_character.SetCharacterizeOn(True)
        new_character.CreateControlRig(True)

        # sets imported control rig as input
        current_character.InputCharacter = new_character
        current_character.InputType = FBCharacterInputType.kFBCharacterInputCharacter
        current_character.ActiveInput = True

        # plotting
        plot_options = FBPlotOptions()
        plot_options.PlotAllTakes = True
        plot_options.PlotPeriod = FBTime(0, 0, 0, 10, 0, FBTimeMode.kFBTimeMode120Frames)
        # plot_options.PlotPeriod = FBTime(0, 0, 0, pFrame=0, pField=0,
        #     pTimeMode=FBTimeMode.kFBTimeModeCustom, pFramerate=12.0)
        plot_options.UseConstantKeyReducer = False
        current_character.PlotAnimation(
            FBCharacterPlotWhere.kFBCharacterPlotOnSkeleton,
            plot_options)
        current_character.PlotAnimation(
            FBCharacterPlotWhere.kFBCharacterPlotOnControlRig,
            plot_options)

        # cleaning
        objects_to_clean = []
        rig = new_character.GetCurrentControlSet()
        objects_to_clean.append(rig)
        objects_to_clean.append(new_character)
        model_reference = FBFindModelByName('BVH:reference')
        prepare_cleaning(objects_to_clean, model_reference)
        map(FBComponent.FBDelete, objects_to_clean)
        del objects_to_clean

        time_start = FBTime(0, 0, 0,
            FRAME_BEGINNING - 2, 0, FBTimeMode.kFBTimeModeCustom, 12)
        time_stop = player.ZoomWindowStop
        time_stop_latest = FBTime(0, 0, 0,
            FRAME_BEGINNING + 120, 0, FBTimeMode.kFBTimeModeCustom, 12)
        time_stop = early_time(time_stop, time_stop_latest)
        options.TimeSpan = FBTimeSpan(time_start, time_stop)

        # finally, renders the scene
        for cam_id, cam_pos in enumerate(camera_list):
            update_camera_pos(pos_constraint, cam_pos)
            reset_player(player)
            dst_path = get_dst_path(fbx_file, bvh_file, cam_id)
            options.OutputFileName = dst_path
            app.FileRender(options)
            discard_frames(dst_path)


    for bvh in bvh_list:
        process_bvh(bvh)


fbx_list = all_files(FBX_FOLDER, '.fbx')
bvh_list = all_files(BVH_FOLDER, '.bvh')
camera_list = calc_camera_pos(225, 35, 8)

for fbx in fbx_list:
    process_fbx(fbx, bvh_list)
