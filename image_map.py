
# Import from itools
from itools.handlers import Text, Image as iImage
from itools.stl import stl
from itools.cms.base import Node
from itools.cms.folder import Folder
from itools.xhtml import sanitize_str
from itools.xml import Parser



class Image(Node, iImage):

    def _get_mtime(self):
        return self.timestamp


    def new(self):
        iImage.new(self)
        self.size = None
        self.thumbnails = None


    GET__access__ = True # XXX
    GET__mtime__ = _get_mtime
    def GET(self, context):
        # Content-Type
        mimetype = self.get_mimetype()
        context.response.set_header('Content-Type', mimetype)

        return self.to_str()



class Map(Text):
    """
    <map name="ImageMap">
      <area shape="rect" href="" coords="366,106,399,120" alt="Japon"></area>
      <area shape="rect" href="" coords="32,40,382,420" alt="Australie"></area>
    </map>
    """

    def new(self):
        Text.new(self, data=u'<?xml version="1.0" encoding="UTF-8" ?>\n'
                            u'<map name="ImageMap">\n'
                            u'</map>')



class ImageMap(Folder):

    class_id = 'ImageMap'
    class_layout = {
        '.image': Image,
        '.map': Map}
    class_title = u'Image Map'
    class_icon48 = 'abakuc/images/ImageMap48.png'
    class_icon16 = 'abakuc/images/ImageMap16.png'
    class_description = 'Image with an editable Map'
    class_views = [['view'],
                   ['edit_form'],
                   ['upload_form']]


    def new(self):
        Folder.new(self)
        self.cache['.map'] = Map()
        self.cache['.image'] = Image()


    upload_form__access__ = 'is_allowed_to_edit'
    upload_form__label__ = u'Edit image'
    def upload_form(self, context):
        handler = self.get_handler('/ui/abakuc/map/upload.xml')
        return stl(handler)


    upload__access__ = 'is_allowed_to_edit'
    def upload(self, context):
        file = context.get_form_value('file')
        if not file:
            return context.come_back(u'No file has been entered.')

        # Build a resource with the uploaded data
        filename, mimetype, data = file
        # Check wether the handler is able to deal with the uploaded file
        image = self.get_handler('.image')
        try:
            image.load_state_from_string(data)
        except:
            message = u'The uploaded file does not match this document type.'
            return context.come_back(message)

        return context.come_back(u'Version uploaded.', goto=';preview')


    #######################################################################
    # View
    view__access__ = 'is_allowed_to_view_map'
    view__label__ = u'View'
    def view(self, context):
        map = self.get_handler('.map')
        namespace = {'map': Parser(map.to_str())}
        handler = self.get_handler('/ui/abakuc/map/view.xml')
        return stl(handler, namespace)


    #######################################################################
    # Edit map
    edit_form__access__ = 'is_allowed_to_edit_map'
    edit_form__label__ = u'Edit image map'
    def edit_form(self, context):
        namee = {}
        map = self.get_handler('.map')
        namespace['map'] = {'value': map.to_str()}

        handler = self.get_handler('/ui/abakuc/map/edit.xml')
        return stl(handler, namespace)


    edit_map__access__ = 'is_allowed_to_edit_map'
    def edit(self, context):
        map = context.get_form_value('map')

        data = '<?xml version="1.0" encoding="UTF-8" ?>\r\n'
        if data not in map:
            map = data + map

        map_handler = self.get_handler('.map')
        try:
            # Check wether the handler is able to deal with the map code
            sanitize_str(map)
            map_handler.load_state_from_string(map)
        except:
            return context.come_back(u'The map field is not well formed.')

        return context.come_back(u'Map changed.', goto=';view')
