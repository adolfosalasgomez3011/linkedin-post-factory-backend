'' Launches voice corpus watcher silently (no console window)
'' Place a shortcut to this file in:
''   shell:startup  (Win+R, type shell:startup, paste shortcut there)
'' to auto-start on login.

Dim WShell
Set WShell = CreateObject("WScript.Shell")
WShell.Run "cmd /c ""C:\Users\USER\OneDrive\LinkedIn_PersonalBrand\Post_Factory_App\start_voice_watcher.bat""", 0, False
Set WShell = Nothing
