' ═══════════════════════════════════════════════════════════════════════════
' SamarthX AI Services - Silent Windows Background Launcher (VBScript)
' ═══════════════════════════════════════════════════════════════════════════
' Launches service_manager silently with no persistent console window.
' ═══════════════════════════════════════════════════════════════════════════

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

strScriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
pythonExe = strScriptDir & "\venv_310\Scripts\python.exe"

If Not fso.FileExists(pythonExe) Then
    pythonExe = "python.exe"
End If

cmd = Chr(34) & pythonExe & Chr(34) & " -m ai_integration.service_manager start"
WshShell.CurrentDirectory = strScriptDir
WshShell.Run cmd, 0, False
Set WshShell = Nothing
Set fso = Nothing
