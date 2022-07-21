import re

fi= open("C:\src\qudi\gui\\laserscanner\\ui_laserscanner_gui.ui","r")
lines=fi.readlines()
fi.close()

logicstring="self._voltscan_logic" # the path to the logic from the gui

connectorstring="" # should be used in the gui on_activate
disconnectorstring="" # should be used in the gui on_deactivate
funcdefs="" # should be used in the logic
variables="" # should be used in the logic before the init
setdefault="" # should be used in the gui on_activate


for line in lines:
    	#print(line)
        if "ple_" in line:# and("NumberOfLines" in line):
            if "_Button" in line or "_pushButton" in line :
                #print(line)
                result = re.search('name="(.*?)"', line)
                #print(result)
                if result != None:
                    #print(result.group(1))
                    connectorstring=connectorstring+f"self._mw.{result.group(1)}.clicked.connect({logicstring}.{result.group(1)}_Clicked)\n"
                    disconnectorstring=disconnectorstring+f"self._mw.{result.group(1)}.clicked.disconnect()\n"
                    funcdefs=funcdefs + f"def {result.group(1)}_Clicked(self,on):\n\tprint('done something with {result.group(1)}')\n\n"

            elif "_CheckBox" in line or "_checkBox" in line:
                result = re.search('name="(.*?)"', line)
                if result != None:
                    connectorstring=connectorstring+f"self._mw.{result.group(1)}.stateChanged.connect({logicstring}.{result.group(1)}_StateChanged)\n"
                    disconnectorstring=disconnectorstring+f"self._mw.{result.group(1)}.stateChanged.disconnect()\n"
                    funcdefs=funcdefs + f"def {result.group(1)}_StateChanged(self,on):\n\tprint('done something with {result.group(1)}')\n\tself.{result.group(1)[:-9]}=on==2\n\n"
                    variables=variables + f"{result.group(1)[:-9]}:bool\n"
                    setdefault=setdefault +f"self._mw.{result.group(1)}.setChecked({logicstring}.{result.group(1)[:-9]})\n"

            elif "_LineEdit" in line or "_lineEdit" in line:
                result = re.search('name="(.*?)"', line)
                if result != None:
                    dofloat=False
                    if "name" not in result.group(1):
                        dofloat=True
                    connectorstring=connectorstring+f"self._mw.{result.group(1)}.textEdited.connect({logicstring}.{result.group(1)}_textEdited)\n"
                    disconnectorstring=disconnectorstring+f"self._mw.{result.group(1)}.textEdited.disconnect()\n"
                    funcdefs=funcdefs + f"def {result.group(1)}_textEdited(self,text):\n\tprint('done something with {result.group(1)}. Text=',text)\n\ttry:\n\t\tself.{result.group(1)[:-9]}={'float('*dofloat}text{')'*dofloat}\n\texcept:\n\t\tpass\n\n"
                    variables=variables + f"{result.group(1)[:-9]}:{'str'*(not dofloat)+'float'*dofloat}\n"
                    setdefault=setdefault+f"self._mw.{result.group(1)}.setText(str({logicstring}.{result.group(1)[:-9]}))\n"

            elif "_DoubleSpinBox" in line or "_doubleSpinBox" in line: 
                result = re.search('name="(.*?)"', line)
                if result != None:
                    connectorstring=connectorstring+f"self._mw.{result.group(1)}.valueChanged.connect({logicstring}.{result.group(1)}_Edited)\n"
                    disconnectorstring=disconnectorstring+f"self._mw.{result.group(1)}.valueChanged.disconnect()\n"
                    funcdefs=funcdefs + f"def {result.group(1)}_Edited(self,value):\n\tprint('done something with {result.group(1)}. Value=',value)\n\tself.{result.group(1)[:-14]}=value\n\n"
                    variables=variables + f"{result.group(1)[:-14]}:float\n"
                    setdefault=setdefault+f"self._mw.{result.group(1)}.setValue({logicstring}.{result.group(1)[:-14]})\n"

print(variables,funcdefs,connectorstring,setdefault,disconnectorstring,sep="\n")
