#  Copyright 2020 Parakoopa
#
#  This file is part of SkyTemple.
#
#  SkyTemple is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  SkyTemple is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with SkyTemple.  If not, see <https://www.gnu.org/licenses/>.
import logging
import os
import sys
from functools import partial

from skytemple.core.error_handler import display_error
from skytemple.core.ui_utils import add_dialog_png_filter
from skytemple_tilequant.aikku.image_converter import AikkuImageConverter

try:
    from PIL import Image
except ImportError:
    from pil import Image
from gi.repository import Gtk
logger = logging.getLogger(__name__)


class TilequantController:
    """A dialog controller as an UI for tilequant."""
    def __init__(self, parent_window: Gtk.Window, builder: Gtk.Builder):
        self.window: Gtk.Window = builder.get_object('dialog_tilequant')
        self.window.set_transient_for(parent_window)
        self.window.set_attached_to(parent_window)
        
        # Filters
        png_filter = Gtk.FileFilter()
        png_filter.set_name("PNG image (*.png)")
        png_filter.add_mime_type("image/png")
        png_filter.add_pattern("*.png")

        jpg_filter = Gtk.FileFilter()
        jpg_filter.set_name("JPEG image (*.jpg, *.jpeg)")
        jpg_filter.add_mime_type("image/jpge")
        jpg_filter.add_pattern("*.jpg")
        jpg_filter.add_pattern("*.jpeg")

        any_filter = Gtk.FileFilter()
        any_filter.set_name("Any files")
        any_filter.add_pattern("*")

        tq_input_file: Gtk.FileChooserButton = builder.get_object('tq_input_file')
        tq_input_file.add_filter(png_filter)
        tq_input_file.add_filter(jpg_filter)
        tq_input_file.add_filter(any_filter)

        tq_second_file: Gtk.FileChooserButton = builder.get_object('tq_second_file')
        tq_second_file.add_filter(png_filter)
        tq_second_file.add_filter(jpg_filter)
        tq_second_file.add_filter(any_filter)

        builder.get_object('tq_number_palettes_help').connect('clicked', partial(
            self.show_help, 'The maximum number of palettes that can be used. For normal backgrounds, '
                            'this can be a max. of 16. For map backgrounds, both layers share in total 14 palettes '
                            '(since the last 2 palettes are not rendered in game).'
        ))
        builder.get_object('tq_transparent_color_help').connect('clicked', partial(
            self.show_help, 'This exact color of the image will be imported as transparency (default: #12ab56).'
        ))
        builder.get_object('tq_second_file_help').connect('clicked', partial(
            self.show_help, 'You can use this to convert multiple images at once with the same palettes. '
                            'This is useful for map backgrounds with multiple layers, that need to share the same'
                            'palettes.'
        ))
        builder.get_object('tq_convert').connect('clicked', self.convert)
        self.builder = builder
        self._previous_output_image = None
        self._previous_second_output_image = None

    def run(self, num_pals=16, num_colors=16):
        """
        Shows the tilequant dialog. Doesn't return anything.
        """
        self.builder.get_object('tq_number_palettes').set_text(str(num_pals))
        self.window.run()
        self.window.hide()

    def convert(self, *args):

        has_first_image = self.builder.get_object('tq_input_file').get_filename() is not None
        has_second_image = self.builder.get_object('tq_second_file').get_filename() is not None

        if not has_first_image:
            self.error("Please select an input image.")
            return
        if has_second_image:
            md = Gtk.MessageDialog(self.window,
                                   Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                                   Gtk.ButtonsType.OK, "Since you selected two images to convert, you will be asked "
                                                       "for both images where to save them to.")
            md.run()
            md.destroy()

        dialog = Gtk.FileChooserDialog(
            "Save first image as (PNG)...",
            self.window,
            Gtk.FileChooserAction.SAVE,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        )
        if self._previous_output_image is not None:
            dialog.set_filename(self._previous_output_image)

        add_dialog_png_filter(dialog)

        response = dialog.run()
        output_image = dialog.get_filename()
        if '.' not in output_image:
            output_image += '.png'
        self._previous_output_image = output_image
        dialog.destroy()
        if response != Gtk.ResponseType.OK:
            return

        if has_second_image:
            dialog = Gtk.FileChooserDialog(
                "Save second image as (PNG)...",
                self.window,
                Gtk.FileChooserAction.SAVE,
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
            )
            if self._previous_second_output_image is not None:
                dialog.set_filename(self._previous_second_output_image)
            else:
                dialog.set_filename(output_image)

            add_dialog_png_filter(dialog)

            response = dialog.run()
            second_output_image = dialog.get_filename()
            if '.' not in second_output_image:
                second_output_image += '.png'
            self._previous_second_output_image = second_output_image
            dialog.destroy()
            if response != Gtk.ResponseType.OK:
                return

        try:
            num_pals = int(self.builder.get_object('tq_number_palettes').get_text())
            input_image = self.builder.get_object('tq_input_file').get_filename()
            second_input_file = self.builder.get_object('tq_second_file').get_filename()
            transparent_color = self.builder.get_object('tq_transparent_color').get_color()
            transparent_color = (
                int(transparent_color.red_float * 255),
                int(transparent_color.green_float * 255),
                int(transparent_color.blue_float * 255)
            )
        except ValueError:
            self.error("You entered invalid numbers.")
        else:
            if not os.path.exists(input_image):
                self.error("The input image does not exist.")
                return
            if has_second_image and not os.path.exists(second_input_file):
                self.error("The second input image does not exist.")
                return
            with open(input_image, 'rb') as input_file:
                try:
                    if not has_second_image:
                        # Only one image
                        image = Image.open(input_file)
                    else:
                        # Two images: Merge them.
                        image1 = Image.open(input_file)
                        image2 = Image.open(second_input_file)
                        image = Image.new(
                            'RGB',
                            (max(image1.width, image2.width), image1.height + image2.height),
                            transparent_color
                        )
                        image.paste(image1, (0, 0))
                        image.paste(image2, (0, image1.height))
                except OSError:
                    self.error("The input image is not a supported format.")
                    return
                try:
                    converter = AikkuImageConverter(image, transparent_color)
                    img = converter.convert(num_pals)
                    if not has_second_image:
                        # Only one image
                        img.save(output_image)
                    else:
                        # Two images: Un-merge them.
                        img.crop((0, 0, image1.width, image1.height)).save(output_image)
                        img.crop((0, image1.height, image2.width, image1.height + image2.height)).save(second_output_image)
                except BaseException as err:
                    logger.error("Tilequant error.", exc_info=err)
                    self.error(str(err))
                else:
                    md = Gtk.MessageDialog(self.window,
                                           Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                                           Gtk.ButtonsType.OK, "Image was conveted.")
                    md.run()
                    md.destroy()

    def show_help(self, info, *args):
        md = Gtk.MessageDialog(self.window,
                               Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                               Gtk.ButtonsType.OK, info)
        md.run()
        md.destroy()

    def error(self, msg):
        display_error(
            sys.exc_info(),
            msg
        )
