Option Explicit
Dim taskFSO, taskShell, taskRoot, taskBase, taskPython, taskCommand
Set taskFSO = CreateObject("Scripting.FileSystemObject")
Set taskShell = CreateObject("WScript.Shell")
taskRoot = taskFSO.GetParentFolderName(WScript.ScriptFullName)
taskPython = taskRoot & "\.venv\Scripts\pythonw.exe"
If Not taskFSO.FileExists(taskPython) Then
    MsgBox "Python ortami bulunamadi. Once README dosyasindaki kurulumu tamamlayin.", 48, "School Evacuation Pilot"
    WScript.Quit 1
End If
taskCommand = Chr(34) & taskPython & Chr(34) & " " & Chr(34) & taskRoot & "\launch.py" & Chr(34) & " --open"
taskShell.Run taskCommand, 0, False
