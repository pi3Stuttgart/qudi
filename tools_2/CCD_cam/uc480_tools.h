/*
###############################################################################
#                                                                             #
# File:    uc480_tools.h                                                      #
# Project: Library interface for uc480_tools								  #
#          exported API functions                                             #
#                                                                             #
###############################################################################
*/

#ifndef __UC480TOOLS_H__
#define __UC480TOOLS_H__


#ifdef __cplusplus
 extern "C" {
#endif

typedef DWORD HCAM;

// Access mode 
#define IS_FILE_ACCESS_MODE_WRITE 0x01 
#define IS_FILE_ACCESS_MODE_READ  0x02

 // Color modes ------------------------------------------------
#define IS_AVI_CM_RGB32     0	// RGB32
#define IS_AVI_CM_RGB24		1	// RGB24
#define IS_AVI_CM_Y8		6	// Y8
#define IS_AVI_CM_BAYER		11	// Bayer

// Events ------------------------------------------------
#define IS_AVI_SET_EVENT_FRAME_SAVED	1


// error constants --------------------------------------------
#define ISAVIERRBASE    300
#define ISAVIMAKEERR(_x_)               (ISAVIERRBASE + _x_)
#define IS_AVI_NO_ERR                       0
#define IS_AVI_ERR_INVALID_FILE             ISAVIMAKEERR( 1)
#define IS_AVI_ERR_NEW_FAILED               ISAVIMAKEERR( 2)
#define IS_AVI_ERR_CREATESTREAM             ISAVIMAKEERR( 3)
#define IS_AVI_ERR_PARAMETER                ISAVIMAKEERR( 4)
#define IS_AVI_ERR_NO_CODEC_AVAIL           ISAVIMAKEERR( 5)
#define IS_AVI_ERR_INVALID_ID               ISAVIMAKEERR( 6)
#define IS_AVI_ERR_COMPRESS                 ISAVIMAKEERR( 7)
#define IS_AVI_ERR_DECOMPRESS               ISAVIMAKEERR( 8)
#define IS_AVI_ERR_CAPTURE_RUNNING          ISAVIMAKEERR( 9)
#define IS_AVI_ERR_CAPTURE_NOT_RUNNING      ISAVIMAKEERR(10)
#define IS_AVI_ERR_PLAY_RUNNING             ISAVIMAKEERR(11)
#define IS_AVI_ERR_PLAY_NOT_RUNNING         ISAVIMAKEERR(12)
#define IS_AVI_ERR_WRITE_INFO               ISAVIMAKEERR(13)
#define IS_AVI_ERR_INVALID_VALUE            ISAVIMAKEERR(14)
#define IS_AVI_ERR_ALLOC_MEMORY				ISAVIMAKEERR(15)
#define IS_AVI_ERR_INVALID_CM				ISAVIMAKEERR(16)
#define IS_AVI_ERR_COMPRESSION_RUN			ISAVIMAKEERR(17)
#define IS_AVI_ERR_INVALID_SIZE				ISAVIMAKEERR(18)
#define IS_AVI_ERR_INVALID_POSITION			ISAVIMAKEERR(19)
#define IS_AVI_ERR_INVALID_HCAM				ISAVIMAKEERR(20)
#define IS_AVI_ERR_EVENT_FAILED				ISAVIMAKEERR(21)
#define IS_AVI_ERR_EXCEPTION                ISAVIMAKEERR(22)
#define IS_AVI_ERR_GENERIC                  ISAVIMAKEERR(23)
#define IS_AVI_ERR_NOT_SUPPORTED            ISAVIMAKEERR(24)
#define IS_AVI_ERR_FILE_NOT_OPEN            ISAVIMAKEERR(25)
#define IS_AVI_ERR_WRITE_FAILED             ISAVIMAKEERR(26)
#define IS_AVI_ERR_READ_FAILED              ISAVIMAKEERR(27)
#define IS_AVI_ERR_SEEK_FAILED              ISAVIMAKEERR(28)


#define UC480AVIEXP    extern  __declspec(dllexport) INT __stdcall

// function prototyes


/*! \brief Initialises the uc480 AVI interface. 
*
*
*  \param   pnAviID:	After the function call, it contains the instance ID needed by the other functions. 
*						Several instances may be opened at the same time.
*
*  \return	IS_AVI_NO_ERR				No error, initialisation was successful
*  \return	IS_AVI_ERR_PARAMETER		pnAviID points to NULL
*  \return	IS_AVI_ERR_NO_CODEC_AVAIL	The maximum available instances of the interface have been 
*										reached.
***********************************************************************************************************/
UC480AVIEXP isavi_InitAVI				(INT* pnAviID,HCAM hcam);


/*! \brief Ends and frees the instance of the uc480 AVI interface specified by the given instance ID.
*
*
*  \param   nAviID:	Instance ID returned by isavi_InitAVI()
*
*  \return	IS_AVI_NO_ERR			No error, initialisation was successful
*  \return	IS_AVI_ERR_INVALID_ID	The specified instance could not be found. The ID is either invalid or the 
*									specified interface has already been destroyed by a previous call to 
*									isavi_ExitAVI().
*  \return	IS_AVI_ERR_INVALID_FILE	The AVI file could not be closed successfully
***********************************************************************************************************/
UC480AVIEXP isavi_ExitAVI				(INT nAviID);


/*! \brief	Sets the size of the input buffer and the offset of the input data. After this, the function 
*			isavi_AddFrame receives as parameter a pointer to the data to compress, and uses this information 
*			to save only the valid data.
*
*
*  \param   nAviID:		Instance ID returned by isavi_InitAVI()
*  \param	cMode:		Color mode of the input data. There are four supported formats (IS_AVI_CM_RGB32,
*						IS_AVI_CM_RGB24,IS_AVI_CM_Y8 and IS_AVI_CM_BAYER)
*  \param	Width:		Image width
*  \param	Height:		Image height
*  \param	PosX:		Offset in x axis 
*  \param	PosY:		Offset in y axis
*  \param	LineOffset:	Empty position until next image line
*
*  \return	IS_AVI_NO_ERR				No error, initialisation was successful
*  \return	IS_AVI_ERR_INVALID_ID		The specified instance could not be found. The ID is either invalid or the 
*										specified interface has already been destroyed by a previous call to 
*										isavi_ExitAVI().
*  \return	IS_AVI_ERR_INVALID_FILE		The AVI file could not be closed successfully
*  \return	IS_AVI_ERR_CAPTURE_RUNNING	Capture is running
*  \return	IS_AVI_ERR_ALLOC_MEMORY		Error allocating memory
*  \return	IS_AVI_ERR_INVALID_CM		Colour mode not supported
*  \return	IS_AVI_ERR_INVALID_SIZE		Picture size less than 16 x 16 pixels
*  \return	IS_AVI_ERR_INVALID_POSITION	Invalid position
***********************************************************************************************************/
UC480AVIEXP isavi_SetImageSize		(INT nAviID,INT cMode, INT Width, INT Height, INT PosX, INT PosY, INT LineOffset);


/*! \brief Opens an AVI file for recording. 
*
*
*  \param   nAviID:		Instance ID returned by isavi_InitAVI()
*  \param	pFileName:	NULL or pointer to the filename	Name that should be used for the avi file. 
*						If NULL is used, than a Dialog box allowing to select a file appears.
*
*  \return	IS_AVI_NO_ERR			No error, initialisation was successful
*  \return	IS_AVI_ERR_INVALID_ID	The specified instance could not be found. The ID is either invalid or the 
*									specified interface has already been destroyed by a previous call to 
*									isavi_ExitAVI().
*  \return	IS_AVI_ERR_INVALID_FILE	The user did not select a valid file in the dialog box
*			IS_AVI_ERR_NEW_FAILED	Memory allocation failed
*			IS_AVI_ERR_AVIFILEOPEN	The AVI file could not be opened successfully
*			IS_AVI_ERR_CREATESTREAM	The AVI stream could not be created (Recording only)
***********************************************************************************************************/
UC480AVIEXP isavi_OpenAVI				(INT nAviID, const char* strFileName);


/*! \brief Starts the picture compression thread.
*
*
*  \param   nAviID:			Instance ID returned by isavi_InitAVI()
*
*  \return	IS_AVI_NO_ERR			No error, initialisation was successful
*  \return	IS_AVI_ERR_INVALID_ID	The specified instance could not be found. The ID is either invalid or the 
*									specified interface has already been destroyed by a previous call to 
*									isavi_ExitAVI().
* \return	IS_AVI_ERR_INVALID_FILE	The AVI file is not open
***********************************************************************************************************/
UC480AVIEXP isavi_StartAVI			(INT nAviID);


/*! \brief Stops the picture compression thread, the call of isavi_AddFrame is ignored.
*
*
*  \param   nAviID:			Instance ID returned by isavi_InitAVI()
*
*  \return	IS_AVI_NO_ERR			No error, initialisation was successful
*  \return	IS_AVI_ERR_INVALID_ID	The specified instance could not be found. The ID is either invalid or the 
*									specified interface has already been destroyed by a previous call to 
*									isavi_ExitAVI().
* \return	IS_AVI_ERR_INVALID_FILE	The AVI file is not open
***********************************************************************************************************/
UC480AVIEXP isavi_StopAVI				(INT nAviID);
UC480AVIEXP isavi_OpenAVIW		        (INT nAviID, const wchar_t* strFileName);


/*! \brief Add a new frame to the avi sequence.
*
*
*  \param   nAviID:			Instance ID returned by isavi_InitAVI()
*  \param	pcImageMem:		Pointer to data image
*
*  \return	IS_AVI_NO_ERR				No error, initialisation was successful
*  \return	IS_AVI_ERR_INVALID_ID		The specified instance could not be found. The ID is either invalid or the 
*										specified interface has already been destroyed by a previous call to 
*										isavi_ExitAVI().
*  \return	IS_AVI_ERR_INVALID_FILE		The AVI file is not open
*  \return	IS_AVI_ERR_COMPRESSION_RUN	A compression run and can not compress the actual picture
***********************************************************************************************************/
UC480AVIEXP isavi_AddFrame			(INT nAviID,char *pcImageMem);


/*! \brief	Sets the frame rate of the video. The frame rate can be changed at any time if the avi file is 
*			already created.
*
*
*  \param   nAviID:			Instance ID returned by isavi_InitAVI()
*  \param	pcImageMem:		Pointer to data image
*
*  \return	IS_AVI_NO_ERR			No error, initialisation was successful
*  \return	IS_AVI_ERR_INVALID_ID	The specified instance could not be found. The ID is either invalid or the 
*									specified interface has already been destroyed by a previous call to 
*									isavi_ExitAVI().
*  \return	IS_AVI_ERR_WRITE_INFO	The AVI file could not be modified
***********************************************************************************************************/
UC480AVIEXP isavi_SetFrameRate		(INT nAviID,double fr);


/*! \brief	Sets the quality of the actual image that is going to be compressed and added to the video stream. 
*			The quality can be changed at any time. The best image quality is 100 (bigger avi file size) and 
*			the worst is 1.
*
*
*  \param   nAviID:	Instance ID returned by isavi_InitAVI()
*  \param	q:		Quality of compression [1…100] 
*
*  \return	IS_AVI_NO_ERR				No error, initialisation was successful
*  \return	IS_AVI_ERR_INVALID_ID		The specified instance could not be found. The ID is either invalid 
*										for the specified interface has already been destroyed by a previous 
*										call to isavi_ExitAVI().
*  \return	IS_AVI_ERR_INVALID_VALUE	The parameter q is bigger than 100 or less than 1
***********************************************************************************************************/
UC480AVIEXP isavi_SetImageQuality		(INT nAviID,INT q);


/*! \brief	Sets the quality of the actual image that is going to be compressed and added to the video stream. 
*			The quality can be changed at any time. The best image quality is 100 (bigger avi file size) and 
*			the worst is 1.
*
*
*  \param   nAviID:	Instance ID returned by isavi_InitAVI()
*  \param	size:	Size in Kbytes
*
*  \return	IS_AVI_NO_ERR				No error, initialisation was successful
*  \return	IS_AVI_ERR_INVALID_ID		The specified instance could not be found. The ID is either invalid
*										or the specified interface has already been destroyed by a previous 
*										call to isavi_ExitAVI().
***********************************************************************************************************/
UC480AVIEXP isavi_GetAVISize			(INT nAviID,float *size);


/*! \brief	Allows to retrieve the filename of the current AVI file. It is useful when the AVI file has been 
*			opened specifying NULL for the filename (see isavi_OpenAVI()).
*
*
*  \param   nAviID:		Instance ID returned by isavi_InitAVI()
*  \param	strName:	Pointer to a buffer that will receive the filename. The allocated memory must be 
*						sufficient to contain the complete path to the file.
*
*  \return	IS_AVI_NO_ERR			No error, initialisation was successful
*  \return	IS_AVI_ERR_INVALID_ID	The specified instance could not be found. The ID is either invalid
*										or the specified interface has already been destroyed by a previous 
*										call to isavi_ExitAVI().
***********************************************************************************************************/
UC480AVIEXP isavi_GetAVIFileName		(INT nAviID, char* strName);
UC480AVIEXP isavi_GetAVIFileNameW	  	(INT nAviID, wchar_t* strName);



/*! \brief gets the actual number of pictures written in the avi file. 
*
*
*  \param   nAviID:		Instance ID returned by isavi_InitAVI()
*  \param	nFrames:	Number of frames
*
*  \return	IS_AVI_NO_ERR			No error, initialisation was successful
*  \return	IS_AVI_ERR_INVALID_ID	The specified instance could not be found. The ID is either invalid or the 
*									specified interface has already been destroyed by a previous call to 
*									isavi_ExitAVI().
***********************************************************************************************************/
UC480AVIEXP isavi_GetnCompressedFrames(INT nAviID, unsigned long *nFrames);


/*! \brief	Gets the actual number of dropped pictures. It can be caused in two ways:
*				1.	A compression is running and the current isavi_AddFrame call cannot be attended.
*				2.	An error in the compression algorithm has occurred.
*
*
*  \param   nAviID:			Instance ID returned by isavi_InitAVI()
*  \param	nLostFrames:	Number of dropped frames
*
*  \return	IS_AVI_NO_ERR			No error, initialisation was successful
*  \return	IS_AVI_ERR_INVALID_ID	The specified instance could not be found. The ID is either invalid or the 
*									specified interface has already been destroyed by a previous call to 
*									isavi_ExitAVI().
***********************************************************************************************************/
UC480AVIEXP isavi_GetnLostFrames		(INT nAviID, unsigned long *nLostFrames);

 
/*! \brief resets the number of lost frames and saved frames. 
*
*
*  \param   nAviID:		Instance ID returned by isavi_InitAVI()
*
*  \return	IS_AVI_NO_ERR			No error, initialisation was successful
*  \return	IS_AVI_ERR_INVALID_ID	The specified instance could not be found. The ID is either invalid or the 
*									specified interface has already been destroyed by a previous call to 
*									isavi_ExitAVI().
***********************************************************************************************************/
UC480AVIEXP isavi_ResetFrameCounters	(INT nAviID);


/*! \brief Closes a file opened by a previous call to isavi_OpenAVI(). 
*
*
*  \param   nAviID:		Instance ID returned by isavi_InitAVI()
*
*  \return	IS_AVI_NO_ERR			No error, initialisation was successful
*  \return	IS_AVI_ERR_INVALID_ID	The specified instance could not be found. 
*
***********************************************************************************************************/
UC480AVIEXP isavi_CloseAVI			(INT nAviID);


/*! \brief Initializes the event handler by registering the event object in the avi engine 
*
*
*  \param   nAviID:		Instance ID returned by isavi_InitAVI()
*  \param   hEv:		Event handle
*  \param   which:		Event id.(ex: IS_AVI_SET_EVENT_FRAME_SAVED)
*
*  \return	IS_AVI_NO_ERR			No error, Event initialisation was successful
*  \return	IS_AVI_ERR_INVALID_ID	The specified instance could not be found. 
*  \return  IS_AVI_ERR_EVENT_FAILED SetEvent failed
*  \return  IS_AVI_ERR_PARAMETER    Invalid Event id
***********************************************************************************************************/
UC480AVIEXP isavi_InitEvent			(INT nAviID, HANDLE hEv, INT which);

/*! \brief Release of the equipped event object. After the release, the event signalling 
*          of the current event object is allowed. 
*
*
*  \param   nAviID:		Instance ID returned by isavi_InitAVI()
*  \param   which:		Event id.
*
*  \return	IS_AVI_NO_ERR			No error
*  \return	IS_AVI_ERR_INVALID_ID	The specified instance could not be found. 
*  \return  IS_AVI_ERR_PARAMETER    Invalid Event id
***********************************************************************************************************/
UC480AVIEXP isavi_EnableEvent			(INT nAviID, INT which);


/*! \brief blocks the event given here. The event will generally still occur,
*			but not trigger an event signal any more. After this function is called, the application does not
*			notice the blocked events any more. A desired event can be reactivated with isavi_EnableEvent() if
*			required.
*
*
*  \param   nAviID:		Instance ID returned by isavi_InitAVI()
*  \param   which:		Event id.
*
*  \return	IS_AVI_NO_ERR			No error
*  \return	IS_AVI_ERR_INVALID_ID	The specified instance could not be found. 
*  \return  IS_AVI_ERR_PARAMETER    Invalid Event id
***********************************************************************************************************/
UC480AVIEXP isavi_DisableEvent		(INT nAviID, INT which);

/*! \brief Deletes set event object. After deleting it can not be activated with isavi_EnableEvent(). 
*
*
*  \param   nAviID:		Instance ID returned by isavi_InitAVI()
*  \param   which:		Event id.
*
*  \return	IS_AVI_NO_ERR			No error
*  \return	IS_AVI_ERR_INVALID_ID	The specified instance could not be found. 
*  \return  IS_AVI_ERR_PARAMETER    Invalid Event id
***********************************************************************************************************/
UC480AVIEXP isavi_ExitEvent		(INT nAviID, INT which);

/*! \brief Initialises the uEye File interface. 
*
*
*  \param   punFileID:	 After the function call, it contains the instance ID needed by the other functions. 
*						 Several instances may be opened at the same time.
*  \param   nAccessMode: Access mode (Read: IS_FILE_ACCESS_MODE_READ; Write: IS_FILE_ACCESS_MODE_WRITE) 
*
*  \return	IS_AVI_NO_ERR				No error, initialisation was successful
*  \return	IS_AVI_ERR_GENERIC          Generic error
*  \return	IS_AVI_ERR_PARAMETER		pnAviID points to NULL
*  \return	IS_AVI_ERR_NEW_FAILED    	The maximum available instances of the interface have been 
*										reached.
*  \return	IS_AVI_ERR_EXCEPTION		An exception occured
***********************************************************************************************************/
UC480AVIEXP israw_InitFile(UINT* punFileID, INT nAccessMode);

/*! \brief Ends and frees the instance of the uEye AVI interface specified by the given instance ID.
*
*
*  \param   unFileID: Instance ID returned by israw_InitFile()
*
*  \return	IS_AVI_NO_ERR			No error, deinitialisation was successful
*  \return	IS_AVI_ERR_EXCEPTION    An exception occured
***********************************************************************************************************/
UC480AVIEXP israw_ExitFile(UINT unFileID);

/*! \brief	After this, the function israw_AddFrame receives as parameter a pointer to the data
*           and uses this information to save only the valid data.
*
*
*  \param   unFileID:     Instance ID returned by israw_InitFile()
*  \param	Width:		  Image width
*  \param	Height:		  Image height
*  \param	BitsPerPixel: Image depth
*
*  \return	IS_AVI_NO_ERR				No error, initialisation was successful
*  \return	IS_AVI_ERR_GENERIC          Generic error
*  \return	IS_AVI_ERR_INVALID_ID		The specified instance could not be found. The ID is either invalid or the 
*										specified interface has already been destroyed by a previous call to 
*										israw_ExitFile().
*  \return	IS_AVI_ERR_NOT_SUPPORTED	File was opened in "ReadMode" (s. israw_InitFile)
*  \return	IS_AVI_ERR_EXCEPTION        An exception occured
***********************************************************************************************************/
UC480AVIEXP israw_SetImageInfo(UINT unFileID, UINT unWidth, UINT unHeight, UINT unBitsPerPixel);

/*! \brief	Returns the image info
*
*
*  \param   unFileID	     Instance ID returned by israw_InitFile()
*  \param	punWidth:		 Image width
*  \param	punHeight:		 Image height
*  \param	punBitsPerPixel: Image depth
*
*  \return	IS_AVI_NO_ERR				No error, initialisation was successful
*  \return	IS_AVI_ERR_GENERIC          Generic error
*  \return	IS_AVI_ERR_INVALID_ID		The specified instance could not be found. The ID is either invalid or the 
*										specified interface has already been destroyed by a previous call to 
*										israw_ExitFile().
*  \return	IS_AVI_ERR_FILE_NOT_OPEN	File is not open
*  \return	IS_AVI_ERR_EXCEPTION        An exception occured
***********************************************************************************************************/
UC480AVIEXP israw_GetImageInfo(UINT unFileID, UINT* punWidth, UINT* punHeight, UINT* punBitsPerPixel);

/*! \brief Opens an file. 
*
*
*  \param   unFileID:		Instance ID returned by israw_InitFile()
*  \param	strFileName:	the filename - Name that should be used for the file. 
*
*  \return	IS_AVI_NO_ERR			 No error, initialisation was successful
*  \return	IS_AVI_ERR_GENERIC       Generic error
*  \return	IS_AVI_ERR_INVALID_ID	 The specified instance could not be found. The ID is either invalid or the 
*									 specified interface has already been destroyed by a previous call to 
*									 isavi_ExitAVI().
*  \return	IS_AVI_ERR_INVALID_VALUE The user did not select a valid file name
*  \return	IS_AVI_ERR_FILE_NOT_OPEN File could not opened
*  \return	IS_AVI_ERR_EXCEPTION     An exception occured
***********************************************************************************************************/
UC480AVIEXP israw_OpenFile(UINT unFileID, const char* strFileName);

/*! \brief Closes a file opened by a previous call to israw_OpenFile(). 
*
*
*  \param   unFileID:		Instance ID returned by israw_InitFile()
*
*  \return	IS_AVI_NO_ERR			No error, initialisation was successful
*  \return	IS_AVI_ERR_GENERIC      Generic error
*  \return	IS_AVI_ERR_INVALID_ID	The specified instance could not be found. 
*  \return	IS_AVI_ERR_EXCEPTION    An exception occured
***********************************************************************************************************/
UC480AVIEXP israw_CloseFile(UINT unFileID);

/*! \brief Add a new frame to the sequence.
*
*
*  \param   unFileID:        	Instance ID returned by israw_InitFile()
*  \param	pcData:		        Pointer to data image
*  \param	unTimestampDevice:	Timestamp of the image
*
*  \return	IS_AVI_NO_ERR				No error, initialisation was successful
*  \return	IS_AVI_ERR_GENERIC          Generic error
*  \return	IS_AVI_ERR_INVALID_ID		The specified instance could not be found. The ID is either invalid or the 
*										specified interface has already been destroyed by a previous call to 
*										isavi_ExitAVI().
*  \return	IS_AVI_ERR_FILE_NOT_OPEN    File is not open
*  \return	IS_AVI_ERR_NOT_SUPPORTED	File was opened in "ReadMode" (s. israw_InitFile)
*  \return	IS_AVI_ERR_EXCEPTION        An exception occured
***********************************************************************************************************/
UC480AVIEXP israw_AddFrame(UINT unFileID, const char* pcData, UINT64 unTimestampDevice);

/*! \brief Reads the next frame of the sequence.
*
*
*  \param   unFileID:        	Instance ID returned by israw_InitFile()
*  \param	pData:		        Pointer to data image
*  \param	punTimestampDevice:	Timestamp of the image
*
*  \return	IS_AVI_NO_ERR				No error, initialisation was successful
*  \return	IS_AVI_ERR_GENERIC          Generic error
*  \return	IS_AVI_ERR_INVALID_ID		The specified instance could not be found. The ID is either invalid or the 
*										specified interface has already been destroyed by a previous call to 
*										isavi_ExitAVI().
*  \return	IS_AVI_ERR_FILE_NOT_OPEN    File is not open
*  \return	IS_AVI_ERR_NOT_SUPPORTED	File was opened in "WriteMode" (s. israw_InitFile)
*  \return	IS_AVI_ERR_READ_FAILED    	File read failed
*  \return	IS_AVI_ERR_EXCEPTION        An exception occured
***********************************************************************************************************/
UC480AVIEXP israw_GetFrame(UINT unFileID, char* pData, UINT64* punTimestampDevice);

/*! \brief Seeks
*
*
*  \param   unFileID:        	Instance ID returned by israw_InitFile()
*  \param	unFrame:	        Frame to seek (null indexed)
*
*  \return	IS_AVI_NO_ERR				No error, initialisation was successful
*  \return	IS_AVI_ERR_GENERIC          Generic error
*  \return	IS_AVI_ERR_INVALID_ID		The specified instance could not be found. The ID is either invalid or the 
*										specified interface has already been destroyed by a previous call to 
*										isavi_ExitAVI().
*  \return	IS_AVI_ERR_FILE_NOT_OPEN    File is not open
*  \return	IS_AVI_ERR_NOT_SUPPORTED	File was opened in "WriteMode" (s. israw_InitFile)
*  \return	IS_AVI_ERR_SEEK_FAILED    	File seek failed
*  \return	IS_AVI_ERR_EXCEPTION        An exception occured
***********************************************************************************************************/
UC480AVIEXP israw_SeekFrame(UINT unFileID, UINT unFrame);

/*! \brief	Gets the current file size.
*
*
*  \param   unFileID:        	Instance ID returned by israw_InitFile()
*  \param	pfSize:	            Size in Kbytes
*
*  \return	IS_AVI_NO_ERR				No error, initialisation was successful
*  \return	IS_AVI_ERR_GENERIC          Generic error
*  \return	IS_AVI_ERR_INVALID_ID		The specified instance could not be found. The ID is either invalid
*										or the specified interface has already been destroyed by a previous 
*										call to isavi_ExitAVI().
*  \return	IS_AVI_ERR_FILE_NOT_OPEN    File is not open
*  \return	IS_AVI_ERR_EXCEPTION        An exception occured
***********************************************************************************************************/
UC480AVIEXP israw_GetSize(UINT unFileID, float* pfSize);

#ifdef __cplusplus
 }
#endif

#endif // __UC480TOOLS_H__