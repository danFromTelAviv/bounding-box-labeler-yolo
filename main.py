from tkinter import *

import numpy as np
from PIL import Image, ImageTk
import tkinter.ttk as ttk
import os
import glob
import random

# colors for the bounding boxes
COLORS = {}


# noinspection PyUnusedLocal
class LabelTool:
    def __init__(self, master):
        # set up the main frame
        self.parent = master
        self.parent.title("LabelTool")
        self.frame = Frame(self.parent)
        self.frame.pack(fill=BOTH, expand=1)
        self.parent.resizable(width=True, height=True)

        # initialize global state
        self.imageDir = ''
        self.imageList = []
        self.egDir = ''
        self.egList = []
        self.outDir = ''
        self.cur = 0
        self.total = 0
        self.category = None
        self.imageName = ''
        self.img = None
        self.labelFileName = ''
        self.tkImg = None
        self.tmp = []
        self.currentLabelClass = ''
        self.cla_can_temp = []
        self.classCandidateFileName = 'class.txt'

        # initialize mouse state
        self.STATE = dict()
        self.STATE['click'] = 0
        self.STATE['x'], self.STATE['y'] = 0, 0

        # reference to bbox
        self.bboxIdList = []
        self.bboxId = None
        self.bboxList = []
        self.hl = None
        self.vl = None

        # prep for zoom
        self.zoom = 2

        # ----------------- GUI stuff ---------------------
        # dir entry & load
        self.label = Label(self.frame, text="Image Dir:")
        self.label.grid(row=0, column=0, sticky=E)
        self.entry = Entry(self.frame)
        self.entry.grid(row=0, column=1, sticky=W + E)
        self.ldBtn = Button(self.frame, text="Load", command=self.loadDir)
        self.ldBtn.grid(row=0, column=2, sticky=W + E)

        # main panel for labeling
        self.mainPanel = Canvas(self.frame, cursor='tcross')
        self.mainPanel.bind("<Button-1>", self.mouseClick)
        self.mainPanel.bind("<Motion>", self.mouseMove)
        self.parent.bind("<Escape>", self.cancelBBox)  # press <Espace> to cancel current bbox
        self.parent.bind("<Left>", self.prevImage)  # press 'a' to go backforward
        self.parent.bind("<Right>", self.nextImage)  # press 'd' to go forward
        self.parent.bind("<space>", self.addPointToBboxList)  # press space to go forward
        self.parent.bind("<Down>", self.zoom_out)  # press down arrow to zoom out
        self.parent.bind("<Up>", self.zoom_in)  # press up arrow to zoom in
        self.parent.bind("<Delete>", self.delBBox_key)  # press 'delete' to delete selected box
        self.mainPanel.grid(row=1, column=1, rowspan=4, sticky=W + N)

        # choose class
        if os.path.exists(self.classCandidateFileName):
            with open(self.classCandidateFileName, encoding="utf-8") as cf:
                for line in cf.readlines():
                    tmp = line.strip('\n')
                    self.cla_can_temp.append(tmp)
                    COLORS[tmp] = '#%02x%02x%02x' % (
                        random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

        self.className = StringVar()
        self.className.set(self.cla_can_temp[0])
        self.classCandidate = OptionMenu(self.frame, self.className, *self.cla_can_temp, command=self.setClass)
        self.currentLabelClass = self.className.get()  # init
        self.classCandidate.grid(row=1, column=2)

        self.btnClass = Button(self.frame, text='ComfirmClass', command=self.setClass)
        self.btnClass.grid(row=2, column=2, sticky=W + E)

        # showing bbox info & delete bbox
        self.lb1 = Label(self.frame, text='Bounding boxes:')
        self.lb1.grid(row=3, column=2, sticky=W + N)
        self.listbox = Listbox(self.frame, width=22, height=12)
        self.listbox.grid(row=4, column=2, sticky=N + S)
        self.btnDel = Button(self.frame, text='Delete', command=self.delBBox)
        self.btnDel.grid(row=5, column=2, sticky=W + E + N)
        self.btnClear = Button(self.frame, text='ClearAll', command=self.clearBBox)
        self.btnClear.grid(row=6, column=2, sticky=W + E + N)

        # control panel for image navigation
        self.ctrPanel = Frame(self.frame)
        self.ctrPanel.grid(row=7, column=1, columnspan=2, sticky=W + E)
        self.prevBtn = Button(self.ctrPanel, text='<< Prev', width=10, command=self.prevImage)
        self.prevBtn.pack(side=LEFT, padx=5, pady=3)
        self.nextBtn = Button(self.ctrPanel, text='Next >>', width=10, command=self.nextImage)
        self.nextBtn.pack(side=LEFT, padx=5, pady=3)
        self.progLabel = Label(self.ctrPanel, text="Progress:     /    ")
        self.progLabel.pack(side=LEFT, padx=5)
        self.tmpLabel = Label(self.ctrPanel, text="Go to Image No.")
        self.tmpLabel.pack(side=LEFT, padx=5)
        self.idxEntry = Entry(self.ctrPanel, width=5)
        self.idxEntry.pack(side=LEFT)
        self.goBtn = Button(self.ctrPanel, text='Go', command=self.gotoImage)
        self.goBtn.pack(side=LEFT)

        # display mouse position
        self.disp = Label(self.ctrPanel, text='')
        self.disp.pack(side=RIGHT)

        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(4, weight=1)

    def loadDir(self, dbg=False):
        if not dbg:
            s = self.entry.get()
            self.parent.focus()
            self.category = str(s)
        else:
            s = r'./Images/'

        # get image list
        self.imageDir = os.path.join(r'./Images', '%s' % self.category)
        self.imageList = [f for f_ in [glob.glob(os.path.join(self.imageDir, e), recursive=True) for e in
                                       ('.\**\*.JPG', '.\**\*.PNG')] for f in f_][::5]
        # self.imageList = glob.glob(os.path.join(self.imageDir, '.\**\*.JPG'), recursive=True)
        if len(self.imageList) == 0:
            print('No .JPG images found in the specified dir!')
            return

        # default to the 1st image in the collection
        self.cur = 1
        self.total = len(self.imageList)

        # set up output dir
        self.outDir = os.path.join(r'./Labels', '%s' % self.category)
        if not os.path.exists(self.outDir):
            os.mkdir(self.outDir)

        self.loadImage()
        print('%d images loaded from %s' % (self.total, s))

    def rint(self, num):
        return np.int32(np.rint(num))

    def loadImage(self):
        # load image
        imagePath = self.imageList[self.cur - 1]
        self.img = Image.open(imagePath)
        self.img = self.img.resize([int(self.zoom * s) for s in self.img.size])
        self.tkImg = ImageTk.PhotoImage(self.img)
        self.mainPanel.config(width=max(self.tkImg.width(), 400), height=max(self.tkImg.height(), 400))
        self.mainPanel.create_image(0, 0, image=self.tkImg, anchor=NW)
        self.progLabel.config(text="%04d/%04d" % (self.cur, self.total))

        # load labels
        self.clearBBox()
        self.imageName = os.path.split(imagePath)[-1].split('.')[0]
        labelname = self.imageName + '.txt'
        self.labelFileName = os.path.join(self.outDir, labelname)
        self.labelFileName = imagePath.replace('.' + imagePath.split(".")[-1], ".txt")

        if os.path.exists(self.labelFileName):
            with open(self.labelFileName, encoding="utf-8") as f:
                for (i, line) in enumerate(f):
                    tmp2 = [t.strip() for t in line.split()]
                    tmp = [float(t) if idx > 0 else t for idx, t in enumerate(tmp2[-5:]) ]
                    self.bboxList.append(tuple(tmp))
                    try:
                        tmpId = self.mainPanel.create_rectangle(self.rint(float(tmp[1]) * self.zoom),
                                                                self.rint(float(tmp[2]) * self.zoom),
                                                                self.rint(float(tmp[3]) * self.zoom),
                                                                self.rint(float(tmp[4]) * self.zoom), width=2,
                                                                outline=COLORS[tmp[0]])
                    except:
                        hi=5
                    self.bboxIdList.append(tmpId)
                    self.listbox.insert(END, '%s : (%d, %d) -> (%d, %d)' % (tmp[0], int(tmp[1]), int(tmp[2]),
                                                                            int(tmp[3]), int(tmp[4])))
                    self.listbox.itemconfig(len(self.bboxIdList) - 1, fg=COLORS[tmp[0]])

    def saveImage(self):
        with open(self.labelFileName, 'w', encoding="utf-8") as f:
            for bbox in self.bboxList:
                f.write('%s.jpg ' % self.imageName)
                f.write(' '.join(map(str, bbox)) + '\n')
        print('Image No. %d saved' % self.cur)

    def mouseClick(self, event):
        if self.STATE['click'] == 0:
            self.STATE['x'], self.STATE['y'] = self.rint(event.x / self.zoom), self.rint(event.y / self.zoom)
        else:
            x1, x2 = min(self.STATE['x'], event.x), max(self.STATE['x'], event.x)
            y1, y2 = min(self.STATE['y'], event.y), max(self.STATE['y'], event.y)
            self.append_new_bbox(x1, x2, y1, y2)
        self.STATE['click'] = 1 - self.STATE['click']

    def append_new_bbox(self, x1, x2, y1, y2):
        self.bboxList.append((self.currentLabelClass, x1, y1, x2, y2))
        self.bboxIdList.append(self.bboxId)
        self.bboxId = None
        self.listbox.insert(END, '%s : (%d, %d) -> (%d, %d)' % (self.currentLabelClass, x1, y1, x2, y2))
        self.listbox.itemconfig(len(self.bboxIdList) - 1, fg=COLORS[self.currentLabelClass])

    def addPointToBboxList(self, event=None):
        if self.STATE['click'] != 0:
            x1, y1, x2, y2 = self.STATE['x'] - 1, self.STATE['y'] - 1, self.STATE['x'] + 1, self.STATE['y'] + 1
            if self.bboxId:
                self.mainPanel.delete(self.bboxId)
            self.bboxId = self.mainPanel.create_rectangle(self.rint(x1 * self.zoom), self.rint(y1 * self.zoom),
                                                          self.rint(x2 * self.zoom), self.rint(y2 * self.zoom),
                                                          width=2,
                                                          outline=COLORS[self.currentLabelClass])
            self.append_new_bbox(x1, x2, y1, y2)
            self.STATE['click'] = 1 - self.STATE['click']

    def mouseMove(self, event):
        self.disp.config(text='x: %d, y: %d' % (event.x, event.y))
        if self.tkImg:
            if self.hl:
                self.mainPanel.delete(self.hl)
            self.hl = self.mainPanel.create_line(0, event.y, self.tkImg.width(), event.y, width=2)
            if self.vl:
                self.mainPanel.delete(self.vl)
            self.vl = self.mainPanel.create_line(event.x, 0, event.x, self.tkImg.height(), width=2)
        if 1 == self.STATE['click']:
            if self.bboxId:
                self.mainPanel.delete(self.bboxId)
            self.bboxId = self.mainPanel.create_rectangle(self.rint(self.STATE['x'] * self.zoom),
                                                          self.rint(self.STATE['y'] * self.zoom),
                                                          self.rint(event.x * self.zoom),
                                                          self.rint(event.y * self.zoom),
                                                          width=2, outline=COLORS[self.currentLabelClass])

    def cancelBBox(self, event):
        if 1 == self.STATE['click']:
            if self.bboxId:
                self.mainPanel.delete(self.bboxId)
                self.bboxId = None
                self.STATE['click'] = 0

    def delBBox(self):
        sel = self.listbox.curselection()
        if len(sel) != 1:
            return
        idx = int(sel[0])
        self.mainPanel.delete(self.bboxIdList[idx])
        self.bboxIdList.pop(idx)
        self.bboxList.pop(idx)
        self.listbox.delete(idx)

    def delBBox_key(self, event=None):
        self.delBBox()

    def clearBBox(self):
        for idx in range(len(self.bboxIdList)):
            self.mainPanel.delete(self.bboxIdList[idx])
        self.listbox.delete(0, len(self.bboxList))
        self.bboxIdList = []
        self.bboxList = []

    def prevImage(self, event=None):
        self.saveImage()
        if self.cur > 1:
            self.cur -= 1
            self.loadImage()

    def nextImage(self, event=None):
        self.saveImage()
        if self.cur < self.total:
            self.cur += 1
            self.loadImage()

    def gotoImage(self):
        idx = int(self.idxEntry.get())
        if 1 <= idx <= self.total:
            self.saveImage()
            self.cur = idx
            self.loadImage()

    def setClass(self, event=None):
        self.currentLabelClass = self.className.get()
        print('set label class to :', self.currentLabelClass)

    def zoom_in(self, event=None):
        self.zoom *= 1.2
        self.saveImage()
        self.loadImage()

    def zoom_out(self, event=None):
        self.zoom /= 1.2
        self.saveImage()
        self.loadImage()


if __name__ == '__main__':
    root = Tk()
    tool = LabelTool(root)
    tool.loadDir()
    root.resizable(width=True, height=True)
    root.mainloop()
