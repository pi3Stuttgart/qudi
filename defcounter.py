import os

directory="C:\src\qudi\logic\pulsed\\"
files=os.listdir(directory)
#print(os.getcwd())
#print(files)
#input()

#files="C:\src\qudi\gui\pulsed\pulsed_maingui.py"
for fil in files:
    if ".py" in fil:
        fil=directory+fil
        fi= open(fil,"r")
        lines=fi.readlines()
        fi.close()
        #print(lines)
        newlines=[]
        counter=0
        for line in lines:
            newlines.append(line)
            if "def " in line and line[-2:]!=",\n" and ("channel" in line or "_ch" in line or "seque" in line or "block" in line):
                print(line)
                c=0
                while line[c]==" ":
                    c+=1
                #print(c)
                #print("comming"+line[:c]+"end")
                newlines.append(line[:c]+f"    print('{fil}  ',{counter})\n")
            
                counter+=1

        secfi=open(fil,"w")
        secfi.writelines(newlines)
