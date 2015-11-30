from ...core import Store, HoloMap, OrderedDict
from ..renderer import Renderer, MIME_TYPES
from .widgets import BokehScrubberWidget, BokehSelectionWidget

import param
from param.parameterized import bothmethod

from bokeh.embed import notebook_div
from bokeh.models import DataSource
from bokeh.plotting import Figure
from bokeh.protocol import serialize_json


class BokehRenderer(Renderer):

    backend = 'bokeh'

    fig = param.ObjectSelector(default='auto', objects=['html', 'json', 'auto'], doc="""
        Output render format for static figures. If None, no figure
        rendering will occur. """)

    # Defines the valid output formats for each mode.
    mode_formats = {'fig': {'default': ['html', 'json', 'auto']},
                    'holomap': {'default': ['scrubber', 'widgets', 'auto', None]}}

    widgets = {'scrubber': BokehScrubberWidget,
               'widgets': BokehSelectionWidget}

    _loaded = False

    def __call__(self, obj, fmt=None):
        """
        Render the supplied HoloViews component using the appropriate
        backend. The output is not a file format but a suitable,
        in-memory byte stream together with any suitable metadata.
        """
        plot, fmt =  self._validate(obj, fmt)

        if fmt in self.widgets:
            return self.get_widget(plot, fmt)(), {'file-ext':' html',
                                                  'mime_type': MIME_TYPES['html']}
        elif fmt == 'html':
            html = self.figure_data(plot)
            html = '<center>%s</center>' % html
            return html, {'file-ext':fmt, 'mime_type':MIME_TYPES[fmt]}
        elif fmt == 'json':
            plotobjects = [h for handles in plot.traverse(lambda x: x.current_handles)
                           for h in handles]
            data = OrderedDict()
            for plotobj in plotobjects:
                json = plotobj.vm_serialize(changed_only=True)
                data[plotobj.ref['id']] = {'type': plotobj.ref['type'],
                                           'data': json}
            return serialize_json(data), {'file-ext':' json', 'mime_type':MIME_TYPES[fmt]}


    def figure_data(self, plot, fmt='html', **kwargs):
        return notebook_div(plot.state)


    @classmethod
    def plot_options(cls, obj, percent_size):
        """
        Given a holoviews object and a percentage size, apply heuristics
        to compute a suitable figure size. For instance, scaling layouts
        and grids linearly can result in unwieldy figure sizes when there
        are a large number of elements. As ad hoc heuristics are used,
        this functionality is kept separate from the plotting classes
        themselves.

        Used by the IPython Notebook display hooks and the save
        utility. Note that this can be overridden explicitly per object
        using the fig_size and size plot options.
        """
        factor = percent_size / 100.0
        obj = obj.last if isinstance(obj, HoloMap) else obj
        plot = Store.registry[cls.backend].get(type(obj), None)
        options = Store.lookup_options(cls.backend, obj, 'plot').options
        if not hasattr(plot, 'width') or not hasattr(plot, 'height'):
            from .plot import BokehPlot
            plot = BokehPlot
        width = options.get('width', plot.width) * factor
        height = options.get('height', plot.height) * factor
        return dict(options, **{'width':int(width), 'height': int(height)})


    @bothmethod
    def save(self_or_cls, obj, basename, fmt=None, key={}, info={}, options=None, **kwargs):
        """
        Given an object, a basename for the output file, a file format
        and some options, save the element in a suitable format to disk.
        """
        raise NotImplementedError

    @bothmethod
    def get_size(self_or_cls, plot):
        """
        Return the display size associated with a plot before
        rendering to any particular format. Used to generate
        appropriate HTML display.

        Returns a tuple of (width, height) in pixels.
        """
        return (plot.state.height, plot.state.height)


    @classmethod
    def validate(cls, options):
        """
        Validates a dictionary of options set on the backend.
        """
        try:
            import bokeh
            import bokeh.io
        except:
            raise ImportError("Could not import one of bokeh, pandas or scipy.")

        if not cls._loaded:
            bokeh.io.load_notebook()
            cls._loaded = True

