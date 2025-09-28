import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import role

class Herald:
    def __init__(self, description: str, skeleton_limit: int|None =None, strand_bound: int|None =None):
        self.description = description
        self.skeleton_limit = skeleton_limit
        self.strand_bound = strand_bound

    def __str__(self):
        return f"Herald description={self.description}; skeleton limit={self.skeleton_limit or 'default'}; strand bound={self.strand_bound or 'default'}"

    def emit(self):
        '''Emit the S-expression encoded Herald block for the top of the model
        '''
        pieces = ['(herald', self.description, ]
        if self.strand_bound:
            pieces.append(f"(bound {self.strand_bound})")
        if self.skeleton_limit:
            pieces.append(f"(limit {self.skeleton_limit})")
        pieces.append(')')
        return ' '.join(pieces)

class HeraldDialog(tk.Toplevel):
    def __init__(self, owner):
        '''
        owner is an Application derived from tk.Frame
        '''
        tk.Toplevel.__init__(self, owner.master)
        self.owner = owner
        self.resizable(False, False)
        self.title('Edit Herald')
        content = ttk.Frame(self, padding=(3,3,12,12))
        frame = ttk.Frame(content, borderwidth=5, relief="ridge", width=200, height=200)

        if owner.model and owner.model.herald:
            okButton = ttk.Button(frame, text='Okay', command=self.updateHerald)
            self.nameVar = tk.StringVar(value=owner.model.herald.description)
            self.skeletonLimitVar = tk.StringVar(value=owner.model.herald.skeleton_limit or "")
            self.strandBoundVar = tk.StringVar(value=owner.model.herald.strand_bound or "")
        else:
            okButton = ttk.Button(frame, text='Okay', command=self.createHerald)
            self.nameVar = tk.StringVar()
            self.skeletonLimitVar = tk.StringVar()
            self.strandBoundVar = tk.StringVar()

        nameLabel = ttk.Label(frame, text='Model description:')
        nameEntry = ttk.Entry(frame, textvariable=self.nameVar)
        nameEntry['width'] = 30

        skeletonLimitLabel = ttk.Label(frame, text='Skeleton limit (optional):')
        skeletonLimitEntry = ttk.Entry(frame, textvariable=self.skeletonLimitVar)
        skeletonLimitEntry['width'] = 30

        strandBoundLabel = ttk.Label(frame, text='Strand bound (optional):')
        strandBoundEntry = ttk.Entry(frame, textvariable=self.strandBoundVar)
        strandBoundEntry['width'] = 30

        cancelButton = ttk.Button(frame, text='Cancel', command=self.cancelUpdate)

        content.grid(column=0, row=0)
        frame.grid(column=0, row=0, columnspan=3, rowspan=2)
        nameLabel.grid(column=0, row=0)
        nameEntry.grid(column=1, row=0, columnspan=2)
        skeletonLimitLabel.grid(column=0, row=1)
        skeletonLimitEntry.grid(column=1, row=1, columnspan=2)
        strandBoundLabel.grid(column=0, row=2)
        strandBoundEntry.grid(column=1, row=2, columnspan=2)
        okButton.grid(column=0, row=4)
        cancelButton.grid(column=2, row=4)

    def createHerald(self):
        skeleton_limit = self.skeletonLimitVar.get()
        skeleton_limit = int(skeleton_limit) if skeleton_limit else None
        strand_bound = self.strandBoundVar.get()
        strand_bound = int(strand_bound) if strand_bound else None
        herald = Herald(description=self.nameVar.get(), skeleton_limit=skeleton_limit, strand_bound=strand_bound)
        if self.owner.model is None:
            self.owner.model = Model(self.owner)
        self.owner.model.setHerald(herald)
        self.destroy()


    def updateHerald(self):
        herald = self.owner.model.herald
        skeleton_limit = self.skeletonLimitVar.get()
        herald.skeleton_limit = int(skeleton_limit) if skeleton_limit else None
        strand_bound = self.strandBoundVar.get()
        herald.strand_bound = int(strand_bound) if strand_bound else None
        herald.description = self.nameVar.get()

        self.destroy()

    def cancelUpdate(self):
        self.destroy()


class Model:
    def __init__(self, parent):
        self.parent = parent  # Application derived from tkinter root
        self.herald: Herald|None = None
        self.protocol: Protocol|None = None

    def emit(self):
        return '\n'.join([
            self.herald.emit(),
            self.protocol.emit()
        ])

    def setHerald(self, herald):
        self.herald = herald

    def setProtocol(self, protocol):
        self.protocol = protocol

    def __str__(self):
        return f"Model {self.herald!s}; protocol={self.protocol!s}"


class Protocol:
    def __init__(self, parent: Model, name: str, algebra=None):
        assert algebra is None or algebra in {'basic', 'diffie-hellman'}
        self.algebra = algebra if algebra else 'basic'  # default to explicit basic
        self.name = name
        self.roles = []
        self.messages = []

    def emit(self):
        return '\n'.join([
            f"(defprotocol {self.name} {self.algebra}",
            '\n'.join([r.emit() for r in self.roles]),
            ")",
        ])

    def addRole(self, newRole): pass
    def addMessage(self, newRole): pass

class ProtocolDialog(tk.Toplevel):
    def __init__(self, owner):
        '''
        owner is an Application derived from tk.Frame
        '''
        tk.Toplevel.__init__(self, owner.master)
        self.owner = owner
        self.resizable(False, False)
        self.title('Edit Protocol')
        content = ttk.Frame(self, padding=(3,3,12,12))
        frame = ttk.Frame(content, borderwidth=5, relief="ridge", width=200, height=200)

        if owner.model is not None and owner.model.protocol:
            okButton = ttk.Button(frame, text='Okay', command=self.updateProtocol)
            self.nameVar = tk.StringVar(value=owner.model.protocol.name)
            self.algebraVar = tk.StringVar(value=owner.model.protocol.algebra or "basic")
        else:
            okButton = ttk.Button(frame, text='Okay', command=self.createProtocol)
            self.nameVar = tk.StringVar()
            self.algebraVar = tk.StringVar()

        nameLabel = ttk.Label(frame, text='Protocol name:')
        nameEntry = ttk.Entry(frame, textvariable=self.nameVar)
        nameEntry['width'] = 30

        algebraLabel = ttk.Label(frame, text='Algebra:')
        algebraEntryBasic = ttk.Radiobutton(frame, text='basic', variable=self.algebraVar, value='basic')
        algebraEntryDH = ttk.Radiobutton(frame, text='diffie-hellman', variable=self.algebraVar, value='diffie-hellman')

        cancelButton = ttk.Button(frame, text='Cancel', command=self.cancelUpdate)

        content.grid(column=0, row=0)
        frame.grid(column=0, row=0, columnspan=3, rowspan=2)
        nameLabel.grid(column=0, row=0)
        nameEntry.grid(column=1, row=0, columnspan=2)
        algebraLabel.grid(column=0, row=1)
        algebraEntryBasic.grid(column=1, row=2, columnspan=2)
        algebraEntryDH.grid(column=1, row=3, columnspan=2)
        okButton.grid(column=0, row=5)
        cancelButton.grid(column=2, row=5)

    def createProtocol(self):
        protocol = Protocol(parent=self.owner, name=self.nameVar.get(), algebra=self.algebraVar.get())
        if self.owner.model is None:
            self.owner.model = Model(self.owner)
        self.owner.model.setProtocol(protocol)
        self.destroy()


    def updateProtocol(self):
        protocol = self.owner.model.protocol
        protocol.algebra = self.algebraVar.get()
        protocol.name = self.nameVar.get()

        self.destroy()

    def cancelUpdate(self):
        self.destroy()
