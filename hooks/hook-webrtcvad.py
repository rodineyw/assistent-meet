from PyInstaller.utils.hooks import copy_metadata

# The runtime module is imported as `webrtcvad`, but the installed distribution
# in this project is `webrtcvad-wheels`.
datas = copy_metadata("webrtcvad-wheels")
