import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import role
import model

class Application(tk.Frame):
    def __init__(self, root: tk.Tk|None =None, height=1000, width=1000):
        """
        Initialize the program
        :param root: tk.Tk
        """
        root = tk.Tk() if root is None else root
        super().__init__(root)
        self.master = root
        self.model = None
        self.height= height* 2
        self.width = width * 2
        self.dirty_flag = False
        self.configure_master(height, width)
        self.make_menubar()
        self.initialize_canvas(height, width)

    def configure_master(self, height, width):
        """
        Configure master window's properties
        :return: None
        """
        self.master.title("Visual CPSA")
        self.master.iconbitmap("VCPSA.ico")
        self.master.geometry(f"{height}x{width}")
        self.master.resizable(False, False)

    def initialize_canvas(self, height, width):
        """
        Set up the canvas and place test objects on it
        :return: None
        """
        h = ttk.Scrollbar(self.master, orient=tk.HORIZONTAL)
        v = ttk.Scrollbar(self.master, orient=tk.VERTICAL)
        self.canvas = tk.Canvas(width=width*2, height=height*2, bg="white", scrollregion=(0, 0, height*2, width*2),
                                yscrollcommand=v.set, xscrollcommand=h.set)
        h['command'] = self.canvas.xview
        v['command'] = self.canvas.yview
        self.canvas.grid(column=0, row=0, sticky=(tk.N,tk.W,tk.E,tk.S))
        h.grid(column=0, row=1, sticky=(tk.W,tk.E))
        v.grid(column=1, row=0, sticky=(tk.N,tk.S))
        self.master.grid_columnconfigure(0, weight=1)
        self.master.grid_rowconfigure(0, weight=1)

        self.move_data = {"object": None, "x": 0, "y": 0}

        # self.create_objects("movable")
        # self.bind_tags("movable")

    def create_objects(self, tag):
        """
        Create example objects with given tag
        :param tag: str
        :return: None
        """
        objs = [(200, 200, "cyan"), (400, 400, "red"), (200, 400, "green"), (400, 200, "black")]
        for x, y, color in objs:
            self.canvas.create_oval(x - 30, y - 30, x + 30, y + 30, outline=color, fill=color, tags=tag)

    def bind_tags(self, tag):
        """
        Binding the given tag to events that correspond to drag and drop action
        :param tag: str
        :return: None
        """
        self.canvas.tag_bind(tag, "<ButtonPress-1>", self.move_start)
        self.canvas.tag_bind(tag, "<ButtonRelease-1>", self.move_stop)
        self.canvas.tag_bind(tag, "<B1-Motion>", self.move)


    def move_start(self, event):
        """
        Method that gets called whenever the drag and drop action starts
        :param event: tk.Event
        :return: None
        """
        print(type(event), repr(event))
        x,y = self.canvas.canvasx(event.x),self.canvas.canvasy(event.y)
        self.move_data["object"] = self.canvas.find_closest(x, y)[0]
        self.move_data["x"] = x
        self.move_data["y"] = y
        self.canvas.tag_raise(self.move_data["object"])

    def move_stop(self, event):
        """
        Method that gets called whenever the drag and drop action finishes
        :param event: tk.Event
        :return: None
        """
        print(type(event), repr(event))
        self.move_data["object"] = None
        self.move_data["x"] = 0
        self.move_data["y"] = 0

    def move(self, event):
        """
        Method that gets called while the drag and drop action continues
        :param event: tk.Event
        :return: None
        """
        print(type(event), repr(event))
        x,y = self.canvas.canvasx(event.x),self.canvas.canvasy(event.y)
        dx = x - self.move_data["x"]
        dy = y - self.move_data["y"]

        self.canvas.move(self.move_data["object"], dx, dy)

        self.move_data["x"] = x
        self.move_data["y"] = y

    def make_menubar(self):
        self.master.option_add('*tearOff', tk.FALSE)
        parent = self.master # tk.Toplevel(self.master)
        menubar = tk.Menu(parent)
        parent['menu'] = menubar
        menu_file = tk.Menu(menubar)
        menu_edit = tk.Menu(menubar)
        menubar.add_cascade(menu=menu_file, label='File')
        menubar.add_cascade(menu=menu_edit, label='Edit')
        menu_file.add_command(label='New', command=self.newFile)
        menu_file.add_command(label='Open...', command=self.openFile)
        menu_file.add_command(label='Save', command=self.saveFile)
        menu_file.add_command(label='SaveAs', command=self.saveFileAs)
        menu_file.add_command(label='Export', command=self.exportFile)
        menu_file.add_command(label='Close', command=self.closeFile)
        menu_file.add_command(label='Exit', command=self.exit)

        menu_edit.add_command(label='Herald', command=self.editHerald)
        menu_edit.add_command(label='Protocol', command=self.editProtocol)
        menu_add = tk.Menu(menu_edit)
        menu_edit.add_cascade(menu=menu_add, label='Add')
        menu_add.add_command(label='Role', command=self.addRole)
        menu_add.add_command(label='Message', command=self.addMessage)

    def newFile(self):
        # TODO: check dirty flag and confirm before deleting a current model
        self.model = None
        heraldDialog = model.HeraldDialog(owner=self)
        heraldDialog.mainloop()

    def editProtocol(self):
        protocolDialog = model.ProtocolDialog(owner=self)
        protocolDialog.mainloop()

    def editHerald(self):
        heraldDialog = model.HeraldDialog(owner=self)
        heraldDialog.mainloop()

    def openFile(self):
        filename = filedialog.askopenfilename()
        if filename:
            pass
    def saveFile(self):
        filename = filedialog.asksaveasfilename()
    def saveFileAs(self):
        filename = filedialog.asksaveasfilename()
    def exportFile(self):
        filename = filedialog.asksaveasfilename(filetypes=[("S-expressions", ".scm"),], defaultextension='.scm')
        if filename:
            code = self.model.emit()
            with open(filename, 'w', encoding='utf8') as fptr:
                fptr.write(code)

    def closeFile(self): pass

    def exit(self):
        '''TODO: dirty flag and confirmation dialog before closing
        TODO: Connect Red X to this function
        '''
        self.master.destroy()

    def addRole(self):
        roleDialog = role.RoleDialog(owner=self)
        roleDialog.mainloop()

    def addMessage(self):
        msgDialog = role.MessageDialog(owner=self)
        msgDialog.mainloop()


def main():
    app = Application()
    app.mainloop()


if __name__ == "__main__":
    main()
