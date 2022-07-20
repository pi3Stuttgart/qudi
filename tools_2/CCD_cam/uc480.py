from ctypes import *
import numpy as np


# typedefs
BOOLEAN_T  = c_int32
BOOL_T     = c_int32
INT_T      = c_int32
UINT_T     = c_uint32          
LONG_T     = c_int32           
VOID_T     = c_void_p # void              
LPVOID_T   = c_void_p # void*             
ULONG_T    = c_uint32          
UINT64_T   = c_uint64          
# int64_t           __int64_T
LONGLONG_T = c_int64           
DWORD_T    = c_uint32          
WORD_T     = c_uint16          
BYTE_T     = c_ubyte  # unsigned char     
CHAR_T     = c_char        
TCHAR_T    = c_char              
UCHAR_T    = c_ubyte  # unsigned char     

LPTSTR_T   = POINTER(c_int8)
LPCTSTR_T  = POINTER(c_int8) # const c_int8*     
LPCSTR_T   = POINTER(c_int8) # const c_int8*     
WPARAM_T   = c_uint32          
LPARAM_T   = c_uint32          
LRESULT_T  = c_uint32          
HRESULT_T  = c_uint32          

HWND_T      = c_void_p # void*             
HGLOBAL_T   = c_void_p # void*               
HINSTANCE_T = c_void_p # void*    
HDC_T       = c_void_p # void*             
HMODULE_T   = c_void_p # void*        
HKEY_T      = c_void_p # void*    
HANDLE_T    = c_void_p # void*    

LPBYTE_T    = POINTER(c_byte) # BYTE*             
PDWORD_T    = POINTER(DWORD_T)# DWORD*            
PVOID_T     = c_void_p # VOID*             
PCHAR_T     = c_char_p       


# definition of custom types
HCAM_T = DWORD_T

# live/freeze parameters
IS_GET_LIVE          = 0x8000    
IS_WAIT              = 0x0001    
IS_DONT_WAIT         = 0x0000    
IS_FORCE_VIDEO_STOP  = 0x4000    
IS_FORCE_VIDEO_START = 0x4000    
IS_USE_NEXT_MEM      = 0x8000    


IS_CM_MONO8  = 6    
IS_CM_MONO10 = 34    
IS_CM_MONO12 = 26    
IS_CM_MONO16 = 28    


COLOR_MODES = {
    #IS_CM_SENSOR_RAW16  : { 'bits_per_pixel':4*16, 'dtype':np.},
    #IS_CM_SENSOR_RAW12  : { 'bits_per_pixel':4*16, 'dtype':np.},
    #IS_CM_SENSOR_RAW8   : { 'bits_per_pixel':4*16, 'dtype':np.},    
    
    IS_CM_MONO16        : { 'bits_per_pixel':16, 'dtype':np.uint16},        
    IS_CM_MONO12        : { 'bits_per_pixel':16, 'dtype':np.uint16},       
    IS_CM_MONO8         : { 'bits_per_pixel': 8, 'dtype':np.uint8},
    
    #IS_CM_RGBA12_PACKED : { 'bits_per_pixel':16, 'dtype':np.},   
    #IS_CM_RGB12_PACKED  : { 'bits_per_pixel':16, 'dtype':np.},   
    #IS_CM_RGB10_PACKED  : { 'bits_per_pixel':16, 'dtype':np.},   
    #IS_CM_RGBA8_PACKED  : { 'bits_per_pixel': 8, 'dtype':np.},   
    #IS_CM_RGBY8_PACKED  : { 'bits_per_pixel': 8, 'dtype':np.},   
    #IS_CM_RGB8_PACKED   : { 'bits_per_pixel': 8, 'dtype':np.},   

    #IS_CM_BGRA12_PACKED : { 'bits_per_pixel':16, 'dtype':np.},   
    #IS_CM_BGR12_PACKED  : { 'bits_per_pixel':16, 'dtype':np.},   
    #IS_CM_BGR10_PACKED  : { 'bits_per_pixel':16, 'dtype':np.},   
    #IS_CM_BGRA8_PACKED  : { 'bits_per_pixel': 8, 'dtype':np.},     
    #IS_CM_BGR8_PACKED   : { 'bits_per_pixel': 8, 'dtype':np.}, 
    #IS_CM_BGRY8_PACKED  : { 'bits_per_pixel': 8, 'dtype':np.},     
    #IS_CM_BGR565_PACKED : { 'bits_per_pixel': 5, 'dtype':np.},       
    #IS_CM_BGR5_PACKED   : { 'bits_per_pixel': 5, 'dtype':np.},       
    
    #IS_CM_UYVY_PACKED   : { 'bits_per_pixel': 5, 'dtype':np.}, 
    #IS_CM_UYVY_MONO   : { 'bits_per_pixel': 5, 'dtype':np.}, 
    #IS_CM_UYVY_BAYER   : { 'bits_per_pixel': 5, 'dtype':np.}, 
    #IS_CM_CBYCRY_PACKED   : { 'bits_per_pixel': 5, 'dtype':np.}, 
}



class UC480Exception(Exception):

    @staticmethod
    def get_error_message_from_error_number(no):
        for e_msg, e_no in UC480Exception.is_error_codes.items():  # for name, age in dictionary.iteritems():  (for Python 2.x)
            if e_no == no:   
                return e_msg

    is_error_codes = {
        'IS_NO_SUCCESS' : -1,    # function call failed
        'IS_SUCCESS' : 0,    # function call succeeded
        'IS_INVALID_CAMERA_HANDLE' : 1,    # camera handle is not valid or zero
        'IS_INVALID_HANDLE' : 1,    # a handle other than the camera handle is invalid

        'IS_IO_REQUEST_FAILED' : 2,    # an io request to the driver failed
        'IS_CANT_OPEN_DEVICE' : 3,    # returned by is_InitCamera
        'IS_CANT_CLOSE_DEVICE' : 4,   
        'IS_CANT_SETUP_MEMORY' : 5,    
        'IS_NO_HWND_FOR_ERROR_REPORT' : 6,
        'IS_ERROR_MESSAGE_NOT_CREATED' : 7,    
        'IS_ERROR_STRING_NOT_FOUND' : 8,    
        'IS_HOOK_NOT_CREATED' : 9,    
        'IS_TIMER_NOT_CREATED' : 10,    
        'IS_CANT_OPEN_REGISTRY' : 11,    
        'IS_CANT_READ_REGISTRY' : 12,    
        'IS_CANT_VALIDATE_BOARD' : 13,    
        'IS_CANT_GIVE_BOARD_ACCESS' : 14,    
        'IS_NO_IMAGE_MEM_ALLOCATED' : 15,    
        'IS_CANT_CLEANUP_MEMORY' : 16,    
        'IS_CANT_COMMUNICATE_WITH_DRIVER' : 17,    
        'IS_FUNCTION_NOT_SUPPORTED_YET' : 18,    
        'IS_OPERATING_SYSTEM_NOT_SUPPORTED' : 19,    

        'IS_INVALID_VIDEO_IN' : 20,
        'IS_INVALID_IMG_SIZE' : 21,   
        'IS_INVALID_ADDRESS' : 22,    
        'IS_INVALID_VIDEO_MODE' : 23,    
        'IS_INVALID_AGC_MODE' : 24,    
        'IS_INVALID_GAMMA_MODE' : 25,    
        'IS_INVALID_SYNC_LEVEL' : 26,    
        'IS_INVALID_CBARS_MODE' : 27,    
        'IS_INVALID_COLOR_MODE' : 28,    
        'IS_INVALID_SCALE_FACTOR' : 29,    
        'IS_INVALID_IMAGE_SIZE' : 30,    
        'IS_INVALID_IMAGE_POS' : 31,    
        'IS_INVALID_CAPTURE_MODE' : 32,    
        'IS_INVALID_RISC_PROGRAM' : 33,    
        'IS_INVALID_BRIGHTNESS' : 34,    
        'IS_INVALID_CONTRAST' : 35,    
        'IS_INVALID_SATURATION_U' : 36,    
        'IS_INVALID_SATURATION_V' : 37,    
        'IS_INVALID_HUE' : 38,    
        'IS_INVALID_HOR_FILTER_STEP' :                                                  39,    
        'IS_INVALID_VERT_FILTER_STEP' :                                                40,    
        'IS_INVALID_EEPROM_READ_ADDRESS' :                                              41,    
        'IS_INVALID_EEPROM_WRITE_ADDRESS' :                                             42,    
        'IS_INVALID_EEPROM_READ_LENGTH' :                                               43,    
        'IS_INVALID_EEPROM_WRITE_LENGTH' :                                              44,    
        'IS_INVALID_BOARD_INFO_POINTER' :                                               45,    
        'IS_INVALID_DISPLAY_MODE' :                                                     46,    
        'IS_INVALID_ERR_REP_MODE' :                                                     47,    
        'IS_INVALID_BITS_PIXEL' :                                                       48,    
        'IS_INVALID_MEMORY_POINTER' :                                                   49,

        'IS_FILE_WRITE_OPEN_ERROR' :                                                    50,    
        'IS_FILE_READ_OPEN_ERROR' :                                                     51,    
        'IS_FILE_READ_INVALID_BMP_ID' :                                                 52,    
        'IS_FILE_READ_INVALID_BMP_SIZE' :                                               53,    
        'IS_FILE_READ_INVALID_BIT_COUNT' :                                              54,    
        'IS_WRONG_KERNEL_VERSION' :                                                     55,

        'IS_RISC_INVALID_XLENGTH' :                                                     60,    
        'IS_RISC_INVALID_YLENGTH' :                                                     61,    
        'IS_RISC_EXCEED_IMG_SIZE' :                                                     62,    

        # DirectDraw Mode errors
        'IS_DD_MAIN_FAILED' :                                                           70,    
        'IS_DD_PRIMSURFACE_FAILED' :                                                    71,    
        'IS_DD_SCRN_SIZE_NOT_SUPPORTED' :                                               72,    
        'IS_DD_CLIPPER_FAILED' :                                                        73,    
        'IS_DD_CLIPPER_HWND_FAILED' :                                                   74,    
        'IS_DD_CLIPPER_CONNECT_FAILED' :                                                75,    
        'IS_DD_BACKSURFACE_FAILED' :                                                    76,    
        'IS_DD_BACKSURFACE_IN_SYSMEM' :                                                 77,    
        'IS_DD_MDL_MALLOC_ERR' :                                                        78,    
        'IS_DD_MDL_SIZE_ERR' :                                                          79,    
        'IS_DD_CLIP_NO_CHANGE' :                                                        80,    
        'IS_DD_PRIMMEM_NULL' :                                                          81,    
        'IS_DD_BACKMEM_NULL' :                                                          82,    
        'IS_DD_BACKOVLMEM_NULL' :                                                       83,    
        'IS_DD_OVERLAYSURFACE_FAILED' :                                                 84,    
        'IS_DD_OVERLAYSURFACE_IN_SYSMEM' :                                              85,    
        'IS_DD_OVERLAY_NOT_ALLOWED' :                                                   86,    
        'IS_DD_OVERLAY_COLKEY_ERR' :                                                    87,    
        'IS_DD_OVERLAY_NOT_ENABLED' :                                                   88,    
        'IS_DD_GET_DC_ERROR' :                                                          89,    
        'IS_DD_DDRAW_DLL_NOT_LOADED' :                                                  90,    
        'IS_DD_THREAD_NOT_CREATED' :                                                    91,    
        'IS_DD_CANT_GET_CAPS' :                                                         92,    
        'IS_DD_NO_OVERLAYSURFACE' :                                                     93,    
        'IS_DD_NO_OVERLAYSTRETCH' :                                                     94,    
        'IS_DD_CANT_CREATE_OVERLAYSURFACE' :                                            95,    
        'IS_DD_CANT_UPDATE_OVERLAYSURFACE' :                                            96,    
        'IS_DD_INVALID_STRETCH' :                                                       97,

        'IS_EV_INVALID_EVENT_NUMBER' :                                                 100,    
        'IS_INVALID_MODE' :                                                            101,    
        'IS_CANT_FIND_FALCHOOK' :                                                      102,    
        'IS_CANT_FIND_HOOK' :                                                          102,    
        'IS_CANT_GET_HOOK_PROC_ADDR' :                                                 103,    
        'IS_CANT_CHAIN_HOOK_PROC' :                                                    104,    
        'IS_CANT_SETUP_WND_PROC' :                                                     105,    
        'IS_HWND_NULL' :                                                               106,    
        'IS_INVALID_UPDATE_MODE' :                                                     107,    
        'IS_NO_ACTIVE_IMG_MEM' :                                                       108,    
        'IS_CANT_INIT_EVENT' :                                                         109,    
        'IS_FUNC_NOT_AVAIL_IN_OS' :                                                    110,    
        'IS_CAMERA_NOT_CONNECTED' :                                                    111,    
        'IS_SEQUENCE_LIST_EMPTY' :                                                     112,    
        'IS_CANT_ADD_TO_SEQUENCE' :                                                    113,    
        'IS_LOW_OF_SEQUENCE_RISC_MEM' :                                                114,    
        'IS_IMGMEM2FREE_USED_IN_SEQ' :                                                 115,    
        'IS_IMGMEM_NOT_IN_SEQUENCE_LIST' :                                             116,    
        'IS_SEQUENCE_BUF_ALREADY_LOCKED' :                                             117,    
        'IS_INVALID_DEVICE_ID' :                                                       118,    
        'IS_INVALID_BOARD_ID' :                                                        119,    
        'IS_ALL_DEVICES_BUSY' :                                                        120,    
        'IS_HOOK_BUSY' :                                                               121,    
        'IS_TIMED_OUT' :                                                               122,    
        'IS_NULL_POINTER' :                                                            123,    
        'IS_WRONG_HOOK_VERSION' :                                                      124,    
        'IS_INVALID_PARAMETER' :                                                       125,    # a parameter specified was invalid
        'IS_NOT_ALLOWED' :                                                             126,    
        'IS_OUT_OF_MEMORY' :                                                           127,    
        'IS_INVALID_WHILE_LIVE' :                                                      128,    
        'IS_ACCESS_VIOLATION' :                                                        129,    # an internal exception occurred
        'IS_UNKNOWN_ROP_EFFECT' :                                                      130,    
        'IS_INVALID_RENDER_MODE' :                                                    131,    
        'IS_INVALID_THREAD_CONTEXT' :                                                  132,    
        'IS_NO_HARDWARE_INSTALLED' :                                                   133,    
        'IS_INVALID_WATCHDOG_TIME' :                                                   134,    
        'IS_INVALID_WATCHDOG_MODE' :                                                   135,    
        'IS_INVALID_PASSTHROUGH_IN' :                                                  136,    
        'IS_ERROR_SETTING_PASSTHROUGH_IN' :                                            137,    
        'IS_FAILURE_ON_SETTING_WATCHDOG' :                                             138,    
        'IS_NO_USB20' :                                                                139,   # the usb port doesnt support usb 2.0
        'IS_CAPTURE_RUNNING' :                                                         140,   # there is already a capture running

        'IS_MEMORY_BOARD_ACTIVATED' :                                                  141,    # operation could not execute while mboard is enabled
        'IS_MEMORY_BOARD_DEACTIVATED' :                                                142,    # operation could not execute while mboard is disabled
        'IS_NO_MEMORY_BOARD_CONNECTED' :                                               143,    # no memory board connected
        'IS_TOO_LESS_MEMORY' :                                                         144,    # image size is above memory capacity
        'IS_IMAGE_NOT_PRESENT' :                                                       145,    # requested image is no longer present in the camera
        'IS_MEMORY_MODE_RUNNING' :                                                     146,    
        'IS_MEMORYBOARD_DISABLED' :                                                   147,    

        'IS_TRIGGER_ACTIVATED' :                                                       148,    # operation could not execute while trigger is enabled
        'IS_WRONG_KEY' :                                                               150,    
        'IS_CRC_ERROR' :                                                               151,    
        'IS_NOT_YET_RELEASED' :                                                        152,    # this feature is not available yet
        'IS_NOT_CALIBRATED' :                                                          153,    # the camera is not calibrated
        'IS_WAITING_FOR_KERNEL' :                                                      154,    # a request to the kernel exceeded
        'IS_NOT_SUPPORTED' :                                                           155,    # operation mode is not supported
        'IS_TRIGGER_NOT_ACTIVATED' :                                                   156,    # operation could not execute while trigger is disabled
        'IS_OPERATION_ABORTED' :                                                       157,    
        'IS_BAD_STRUCTURE_SIZE' :                                                      158,    
        'IS_INVALID_BUFFER_SIZE' :                                                     159,    
        'IS_INVALID_PIXEL_CLOCK' :                                                     160,    
        'IS_INVALID_EXPOSURE_TIME' :                                                   161,    
        'IS_AUTO_EXPOSURE_RUNNING' :                                                   162,    
        'IS_CANNOT_CREATE_BB_SURF' :                                                   163,    # error creating backbuffer surface
        'IS_CANNOT_CREATE_BB_MIX' :                                                    164,    # backbuffer mixer surfaces can not be created
        'IS_BB_OVLMEM_NULL' :                                                          165,    # backbuffer overlay mem could not be locked
        'IS_CANNOT_CREATE_BB_OVL' :                                                    166,    # backbuffer overlay mem could not be created
        'IS_NOT_SUPP_IN_OVL_SURF_MODE' :                                               167,    # function not supported in overlay surface mode
        'IS_INVALID_SURFACE' :                                                         168,    # surface invalid
        'IS_SURFACE_LOST' :                                                            169,    # surface has been lost
        'IS_RELEASE_BB_OVL_DC' :                                                       170,    # error releasing backbuffer overlay DC
        'IS_BB_TIMER_NOT_CREATED' :                                                    171,    # backbuffer timer could not be created
        'IS_BB_OVL_NOT_EN' :                                                           172,    # backbuffer overlay has not been enabled
        'IS_ONLY_IN_BB_MODE' :                                                         173,    # only possible in backbuffer mode
        'IS_INVALID_COLOR_FORMAT' :                                                    174,    # invalid color format
        'IS_INVALID_WB_BINNING_MODE' :                                                 175,    # invalid binning mode for AWB
        'IS_INVALID_I2C_DEVICE_ADDRESS' :                                              176,    # invalid I2C device address
        'IS_COULD_NOT_CONVERT' :                                                       177,    # current image couldn't be converted
        'IS_TRANSFER_ERROR' :                                                          178,    # transfer failed
        'IS_PARAMETER_SET_NOT_PRESENT' :                                               179,    # the parameter set is not present
        'IS_INVALID_CAMERA_TYPE' :                                                     180,    # the camera type in the ini file doesn't match
        'IS_INVALID_HOST_IP_HIBYTE' :                                                  181,    # HIBYTE of host address is invalid
        'IS_CM_NOT_SUPP_IN_CURR_DISPLAYMODE' :                                         182,    # color mode is not supported in the current display mode
        'IS_NO_IR_FILTER' : 183,    
        'IS_STARTER_FW_UPLOAD_NEEDED' : 184,    # device starter firmware is not compatible

        'IS_DR_LIBRARY_NOT_FOUND' :                                                    185,    # the DirectRender library could not be found
        'IS_DR_DEVICE_OUT_OF_MEMORY' :                                                 186,    # insufficient graphics adapter video memory
        'IS_DR_CANNOT_CREATE_SURFACE' :                                                187,    # the image or overlay surface could not be created
        'IS_DR_CANNOT_CREATE_VERTEX_BUFFER' :                                          188,    # the vertex buffer could not be created
        'IS_DR_CANNOT_CREATE_TEXTURE' : 189,    # the texture could not be created
        'IS_DR_CANNOT_LOCK_OVERLAY_SURFACE' : 190,    # the overlay surface could not be locked
        'IS_DR_CANNOT_UNLOCK_OVERLAY_SURFACE' : 191,    # the overlay surface could not be unlocked
        'IS_DR_CANNOT_GET_OVERLAY_DC' : 192,    # cannot get the overlay surface DC
        'IS_DR_CANNOT_RELEASE_OVERLAY_DC' : 193,    # cannot release the overlay surface DC
        'IS_DR_DEVICE_CAPS_INSUFFICIENT' : 194,    # insufficient graphics adapter capabilities
        'IS_INCOMPATIBLE_SETTING' :                                                    195,    # Operation is not possible because of another incompatible setting
        'IS_DR_NOT_ALLOWED_WHILE_DC_IS_ACTIVE' :                                       196,    # user App still has DC handle.
        'IS_DEVICE_ALREADY_PAIRED' :                                                   197,    # The device is already paired
        'IS_SUBNETMASK_MISMATCH' :                                                     198,    # The subnetmasks of the device and the adapter differ
        'IS_SUBNET_MISMATCH' :                                                         199,    # The subnets of the device and the adapter differ
        'IS_INVALID_IP_CONFIGURATION' :                                                200,    # The IP configuation of the device is invalid
        'IS_DEVICE_NOT_COMPATIBLE' :                                                   201,    # The device is incompatible to the driver
        'IS_NETWORK_FRAME_SIZE_INCOMPATIBLE' :                                         202,    # The frame size settings of the device and the network adapter are incompatible
        'IS_NETWORK_CONFIGURATION_INVALID' :                                           203,    # The network adapter configuration is invalid
        'IS_ERROR_CPU_IDLE_STATES_CONFIGURATION' :                                     204,    # The setting of the CPU idle state configuration failed
        'IS_DEVICE_BUSY' : 205,    # The device is busy. The operation must be executed again later.
        'IS_SENSOR_INITIALIZATION_FAILED' : 206        
    }

class UC480Camera(object):
    def __init__(self, cam_id=0, dll_path=r"D:\CCD camera THorlabs software\Thorlabs_DCx_Camera_PythonWrapper\uc480_64.dll"):
        self._dll = WinDLL(dll_path)
        self._hcam = HCAM_T(cam_id)
        self._hWnd = HWND_T(0)      # 0: Use DIB mode and now window to open

    @staticmethod
    def _check_error(ret_code):
        if ret_code != 0:
            try:
                _is_ExitCamera()
            except:
                pass
            UC480Exception.is_error_codes
            raise UC480Exception("Error No {}: {}".format(ret_code, UC480Exception.get_error_message_from_error_number(ret_code)) )
    
    def _is_GetNumberOfDevices(self):
        return self._dll.is_GetNumberOfDevices()
        
    def _is_InitCamera(self):
        UC480Camera._check_error(self._dll.is_InitCamera(pointer(self._hcam), self._hWnd))
      
    def _is_ExitCamera(self):
        UC480Camera._check_error(self._dll.is_ExitCamera(self._hcam))
    
    def _is_CaptureVideo(self):
        pass
    
    def _is_FreezeVideo(self, wait):
        if wait == True:
            wait_param = INT_T(IS_WAIT)
        elif wait == False:
            wait_param = INT_T(IS_DONT_WAIT)
        else:
            if wait < 4 or wait > 429496729:
                raise ValueError("Waiting time must be between 4 and 429496729!")
            wait_param =INT_T(wait)
        UC480Camera._check_error(self._dll.is_FreezeVideo(self._hcam, wait_param))
        
        
        
    def _is_CaptureVideo(self, wait):
        if wait == True:
            wait_param = INT_T(IS_WAIT)
        elif wait == False:
            wait_param = INT_T(IS_DONT_WAIT)
        else:
            if wait < 4 or wait > 429496729:
                raise ValueError("Waiting time must be between 4 and 429496729!")
            wait_param =INT_T(wait)
        UC480Camera._check_error(self._dll.is_CaptureVideo(self._hcam, wait_param))
        
        
        
    @staticmethod
    def calc_mem_size(width, height, bits_per_pixel):
        print(width, height, bits_per_pixel)

        line = width * int((bits_per_pixel + 7)/8)
        rest = line % 4
        if rest == 0:
            adjust = 0
        else:
            adjust = (4 - rest)
        size = (line + adjust)*height
        lineinc = line + adjust
        return size
    
    @staticmethod
    def color_mode_to_bits_per_pixel(color_mode):
        return COLOR_MODES[color_mode]["bits_per_pixel"], COLOR_MODES[color_mode]["dtype"]
    
        #### START LIBRARY MANAGED MEMORY
    def _is_AllocImageMem(self, width, height, color_mode):
        bits_per_pixel = UC480Camera.color_mode_to_bits_per_pixel(color_mode)[0]
        size = UC480Camera.calc_mem_size(width, height, bits_per_pixel)
        # image_pointer = ppcImgMem
        ppcImgMem = CHAR_T()
        pid = INT_T(0)
        UC480Camera._check_error(self._dll.is_AllocImageMem(self._hcam, INT_T(width), INT_T(height), INT_T(bits_per_pixel), ppcImgMem, pid))
        #### END LIBARY MANAGED MEMORY
       
        #### START USER MANAGED MEMORY
    def _is_SetAllocatedImageMem(self, width, height, color_mode, memory_id = 0):
        bits_per_pixel, np_dtype = UC480Camera.color_mode_to_bits_per_pixel(color_mode)
        size = width * height
        data = np.zeros((width, height), order='F', dtype=np_dtype)
        data_p = data.__array_interface__['data'][0]
        mem_id = INT_T(memory_id)
        UC480Camera._check_error(self._dll.is_SetAllocatedImageMem(self._hcam, INT_T(width), INT_T(height), INT_T(bits_per_pixel), data_p, pointer(mem_id)))
        return data, mem_id.value
        #### END USER MANAGED MEMORY  
               
    def _is_SetImageMem(self, data, memory_id):
        UC480Camera._check_error(self._dll.is_SetImageMem(self._hcam, data.__array_interface__['data'][0], INT_T(memory_id)))        

    def _is_FreeImageMem(self, data, memory_id):
        UC480Camera._check_error(self._dll.is_FreeImageMem(self._hcam, data.__array_interface__['data'][0], INT_T(memory_id)))

    def _is_SetColorMode(self, color_mode):
        UC480Camera._check_error(self._dll.is_SetColorMode(self._hcam, INT_T(color_mode)))
       
       
    def get_image(self, width=1280, height=1024, color_mode=IS_CM_MONO8):
        try:
            # self._is_InitCamera()
            self._is_SetColorMode(color_mode)
            memory_id = 0
            data, mem_id = self._is_SetAllocatedImageMem(width, height, color_mode, memory_id)
            self._is_SetImageMem(data, mem_id)
            self._is_FreezeVideo(IS_WAIT)
            self._is_FreeImageMem(data, mem_id)
        except Exception as err:
            print(err)
        finally:
            pass
            # self._is_ExitCamera()
        return data
        
        
        
    def get_video(self, width=1280, height=1024, color_mode=IS_CM_MONO8):
        # try:
        self._is_InitCamera()
        self._is_SetColorMode(color_mode)
        memory_id = 0
        data, mem_id = self._is_AllocImageMem(width, height, color_mode)
        self._is_SetImageMem(data, mem_id)
        self._is_CaptureVideo(IS_WAIT)
        self._is_FreeImageMem(data, mem_id)
        # except Exception as err:
        #     print(err)
        # finally:
        self._is_ExitCamera()
        return data    
    
    def _is_Exposure(self):
        #UC480Camera._check_error(self._dll.is_Exposure(self._hcam, UINT nCommand, void* pParam, UINT cbSizeOfParam))
        raise NotImplementedError
        
    def _is_SetHardwareGain(self):
                raise NotImplementedError
    
    def _is_GetAutoInfo():
        raise NotImplementedError

        
    
    
    