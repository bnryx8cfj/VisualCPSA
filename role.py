'''Role objects for VisualCPSA
Roles are both data and graphical objects
Roles extend the Tkinter Line object type from Canvas.create_line
'''
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
#from tkinter import tkFont

class Role:
    def __init__(self, canvas, object_id, name, role_tag, model):
        self.canvas = canvas
        self.object_id = object_id
        self.role_tag = role_tag
        self.name = name
        self.model = model

    def emit(self):
        msgs = []
        for m in self.model.protocol.messages:
            if self.name == m.src:
                msgs.append(f"(send {m.content})")
            elif self.name == m.dst:
                msgs.append(f"(recv {m.content})")
        return '\n'.join([
            f"\t\t(defrole {self.name} \n\t(vars )\n\t(trace",
            "\t)",
            '\n\t'.join(msgs),
            ")",
        ])

class RoleDialog(tk.Toplevel):
    def __init__(self, owner):  # owner is an application derived from tkinter.Frame
        tk.Toplevel.__init__(self, owner.master)
        self.resizable(False, False)
        self.title('Create Role')
        content = ttk.Frame(self, padding=(3,3,12,12))
        frame = ttk.Frame(content, borderwidth=5, relief="ridge", width=200, height=100)

        self.owner = owner
        nameLabel = ttk.Label(frame, text='Role name:')
        self.nameVar = tk.StringVar()
        nameEntry = ttk.Entry(frame, textvariable=self.nameVar)
        nameEntry['width'] = 30
        okButton = ttk.Button(frame, text='Okay', command=self.createRole)
        cancelButton = ttk.Button(frame, text='Cancel', command=self.cancelRole)

        content.grid(column=0, row=0)
        frame.grid(column=0, row=0, columnspan=3, rowspan=2)
        nameLabel.grid(column=0, row=0)
        nameEntry.grid(column=1, row=0, columnspan=2)
        okButton.grid(column=0, row=5)
        cancelButton.grid(column=2, row=5)

    def createRole(self):
        # To do: Gray out until model and protocol are created
        # to do: enforce unique naming or roles
        if self.owner.model and self.owner.model.protocol:
            #canvas_size = self.owner.canvas.size()
            #print(f"{canvas_size=}")
            #width,height = canvas_size
            xgap = 250
            x = len(self.owner.model.protocol.roles) * xgap + xgap//2
            ylo = xgap
            yhi = self.owner.height - xgap
            role_tag = f"Role{len(self.owner.model.protocol.roles):04d}"
            tags = (role_tag, "horizontally_movable")
            object_id = self.owner.canvas.create_line(x,ylo,x,yhi,width=5, tags=tags)
            self.owner.canvas.create_text(x, xgap//2,
                                          # font=tkFont.Font(family='sans', size=18),
                                          text=self.nameVar.get(), tags=tags)
            role_params = dict(canvas=self.owner.canvas, object_id=object_id, name=self.nameVar.get(), role_tag=role_tag, model=self.owner.model)
            role = Role(**role_params)
            print(f"Created role {role_params} line_size={(x,ylo,x,yhi)} {self.owner.canvas.coords(object_id)}{object_id})")
            self.owner.model.protocol.roles.append(role)

        #messagebox.showinfo(title='Not Implemented', message=f"Create role '{self.nameVar.get()}'")
        self.destroy()

    def cancelRole(self):
        self.destroy()

class Message:
    def __init__(self, canvas, object_id, src, dst, message_tag, content):
        self.canvas = canvas
        self.object_id = object_id
        self.src = src
        self.dst = dst
        self.message_tag = message_tag
        self.content = content

class MessageDialog(tk.Toplevel):
    def __init__(self, owner):  # owner is an application derived from tkinter.Frame
        # To do: Make sure source and destination are different
        tk.Toplevel.__init__(self, owner.master)
        self.resizable(False, False)
        self.title('Create Message')
        content = ttk.Frame(self, padding=(3,3,12,12))
        frame = ttk.Frame(content, borderwidth=5, relief="ridge", width=300, height=300)
        self.role_map = {role.name:role for role in owner.model.protocol.roles}

        self.owner = owner
        contentLabel = ttk.Label(frame, text='Message content:')
        self.contentVar = tk.StringVar()
        contentEntry = ttk.Entry(frame, textvariable=self.contentVar)
        contentEntry['width'] = 100

        sourceLabel = ttk.Label(frame, text='Source Role:')
        self.sourceVar = tk.StringVar()
        sourceCtl = ttk.Combobox(frame, textvariable=self.sourceVar)
        sourceCtl['values'] = tuple(self.role_map.keys())
        sourceCtl.state(["readonly"])

        destinationLabel = ttk.Label(frame, text='Destination Role:')
        self.destinationVar = tk.StringVar()
        destinationCtl = ttk.Combobox(frame, textvariable=self.destinationVar)
        destinationCtl['values'] = tuple(self.role_map.keys())
        destinationCtl.state(["readonly"])

        okButton = ttk.Button(frame, text='Okay', command=self.createMessage)
        cancelButton = ttk.Button(frame, text='Cancel', command=self.cancelMessage)

        content.grid(column=0, row=0)
        frame.grid(column=0, row=0, columnspan=5, rowspan=6)
        contentLabel.grid(column=0, row=0)
        contentEntry.grid(column=1, row=0, columnspan=4)
        sourceLabel.grid(column=0, row=2)
        sourceCtl.grid(column=1, row=2, rowspan=3)
        destinationLabel.grid(column=3, row=2)
        destinationCtl.grid(column=4, row=2, rowspan=3)

        okButton.grid(column=0, row=5)
        cancelButton.grid(column=2, row=5)

    def createMessage(self):
        # To do: Gray out until model and protocol are created
        if self.owner.model and self.owner.model.protocol:
            xgap = 250
            src = self.sourceVar.get()
            dst = self.destinationVar.get()
            if src==dst:
                messagebox.showinfo(title='Error', message=f"Source and destination roles must be different {src=} {dst=}")
            elif src not in self.role_map or dst not in self.role_map:
                messagebox.showinfo(title='Error', message=f"{src=} or {dst=} not in existing roles {list(self.role_map.keys())}")
            else:
                y = (len(self.owner.model.protocol.messages) + 3) * xgap // 2
                xsrc = self.owner.canvas.coords(self.role_map[src].object_id)[0]
                xdst = self.owner.canvas.coords(self.role_map[dst].object_id)[0]
                message_tag = f"Message{len(self.owner.model.protocol.messages):04d}"
                tags = (message_tag, "vertically_movable", self.role_map[src].role_tag, self.role_map[dst].role_tag)
                object_id = self.owner.canvas.create_line(xsrc, y, xdst, y, arrow=tk.LAST, arrowshape=(40,50,15),width=5, tags=tags)
                self.owner.canvas.create_text((xsrc + xdst)//2, y - xgap//5,
                                            text=self.contentVar.get(), tags=tags)
                message_params = dict(src=src, dst=dst, canvas=self.owner.canvas, object_id=object_id, content=self.contentVar.get(), message_tag=message_tag)

                # source disk
                self.owner.canvas.create_oval(xsrc - 30, y - 30, xsrc + 30, y + 30, outline='black', fill='black', tags=tags)
                #destination disk
                self.owner.canvas.create_oval(xdst - 30, y - 30, xdst + 30, y + 30, outline='blue', fill='blue', tags=tags)

                msg = Message(**message_params)
                print(f"Created message {message_params} line_size={(xsrc, y, xdst, y)} {self.owner.canvas.coords(object_id)}{object_id})")
                self.owner.model.protocol.messages.append(msg)

        self.destroy()

    def cancelMessage(self):
        self.destroy()

