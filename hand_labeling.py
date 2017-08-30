from caching import cached

import numpy as np
import tkinter as tk
import dataio
import skimage.io
import os
import glob
import random


class BodyPartLabelerGUI(object):
    def __init__(self, master, files, labels):
        self.master = master
        self.files = files
        self.image_width = 512
        self.image_height = 660
        self.last_preview = None
        self.line_stack = []
        self.ans = []
        self.file_index = 0
        self.labels = labels

        self.canvas = tk.Canvas(width=self.image_width, height=self.image_height)
        self.canvas.pack()

        self.label_text = tk.StringVar()
        self.set_label_text()
        self.label = tk.Label(self.master, textvariable=self.label_text)
        self.label.pack()
        self.draw_image()

        self.canvas.bind('<Motion>', self.preview_line)
        self.canvas.bind('<Button-1>', self.create_line)
        self.canvas.bind('<Button-3>', self.remove_line)

    def set_label_text(self):
        labels = self.labels[self.files[self.file_index].split('-')[0]]
        labels = [i+1 for i, label in enumerate(labels) if label]
        self.label_text.set('%4s/%4s | threat zones: %s' % (self.file_index + 1, len(self.files),
                                                            labels))

    def draw_image(self):
        file = self.files[self.file_index]
        self.image = tk.PhotoImage(file=file)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.image)
        self.side_view = int(file.split('.')[0].split('-')[-1]) in (4, 12)

    def horizontal_line(self, y):
        return [self.canvas.create_line(0, y, self.image_width, y, fill='#FF0000')]

    def vertical_line(self, x):
        return [self.canvas.create_line(x, 0, x, self.image_height, fill='#FF0000')]

    def symmetric_line(self, x0, x1):
        return [
            self.vertical_line(x1),
            self.vertical_line(x0 - (x1 - x0))
        ]

    def which_line(self, event):
        if len(self.ans) < 8:
            return self.horizontal_line(event.y), event.y
        else:
            if self.side_view or len(self.ans) == 8:
                return self.vertical_line(event.x), event.x
            else:
                return self.symmetric_line(self.ans[8], event.x), event.x

    def done(self):
        if self.side_view:
            return len(self.ans) == 10
        else:
            return len(self.ans) == 11

    def preview_line(self, event):
        if self.done():
            return
        if self.last_preview is not None:
            for line in self.last_preview:
                self.canvas.delete(line)
        self.last_preview, _ = self.which_line(event)

    def write_output(self):
        out = self.files[self.file_index].replace('.gif', '.npy')
        np.save(out, np.array(self.ans))

        for line in sum(self.line_stack, []):
            self.canvas.delete(line)
        if self.last_preview is not None:
            for line in self.last_preview:
                self.canvas.delete(line)
        self.ans = []
        self.file_index += 1

        if self.file_index == len(self.files):
            self.master.quit()
            return

        self.draw_image()
        self.set_label_text()

    def create_line(self, event):
        if self.done():
            self.write_output()
            return

        lines, ans = self.which_line(event)
        self.ans.append(ans)
        self.line_stack.append(lines)

    def remove_line(self, event):
        if len(self.line_stack) != 0:
            for line in self.line_stack[-1]:
                self.canvas.delete(line)
            self.line_stack.pop()
            self.ans.pop()


@cached(dataio.get_data_generator, version=5)
def get_body_part_labels(mode):
    assert mode in ('sample', 'train')

    for file, data in dataio.get_data_generator(mode, 'aps')():
        for i in range(0, 16, 4):
            out = file.replace('.aps', '-%s.gif' % i)
            if os.path.exists(out):
                continue
            image = np.rot90(data[:, :, i])
            image /= np.max(image)
            if i == 4 or i == 8:
                image = np.fliplr(image)
            skimage.io.imsave(out, image)

    files = [file for file in glob.glob('*.gif')
             if not os.path.exists(file.replace('.gif', '.npy'))]
    random.seed(0)
    random.shuffle(files)
    labels = dataio.get_train_labels()

    root = tk.Tk()
    gui = BodyPartLabelerGUI(root, files, labels)
    root.mainloop()

    assert len(glob.glob('*.gif')) == len(glob.glob('*.npy'))


if __name__ == '__main__':
    get_body_part_labels('sample')