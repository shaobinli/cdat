from .pipeline import Pipeline

import vcs
from vcs import vcs2vtk
import vtk


class VectorPipeline(Pipeline):

    """Implementation of the Pipeline interface for VCS vector plots."""

    def __init__(self, gm, context_):
        super(VectorPipeline, self).__init__(gm, context_)

    def plot(self, data1, data2, tmpl, grid, transform):
        """Overrides baseclass implementation."""
        # Preserve time and z axis for plotting these inof in rendertemplate
        geo = None  # to make flake8 happy
        projection = vcs.elements["projection"][self._gm.projection]
        returned = {}
        taxis = data1.getTime()
        if data1.ndim > 2:
            zaxis = data1.getAxis(-3)
        else:
            zaxis = None

        # Ok get3 only the last 2 dims
        data1 = self._context().trimData2D(data1)
        data2 = self._context().trimData2D(data2)

        scale = 1.0
        lat = None
        lon = None

        latAccessor = data1.getLatitude()
        lonAccesrsor = data1.getLongitude()
        if latAccessor:
            lat = latAccessor[:]
        if lonAccesrsor:
            lon = lonAccesrsor[:]

        gridGenDict = vcs2vtk.genGridOnPoints(data1, self._gm, deep=False, grid=grid,
                                              geo=transform, data2=data2)

        data1 = gridGenDict["data"]
        data2 = gridGenDict["data2"]
        geo = gridGenDict["geo"]

        grid = gridGenDict['vtk_backend_grid']
        xm = gridGenDict['xm']
        xM = gridGenDict['xM']
        ym = gridGenDict['ym']
        yM = gridGenDict['yM']
        continents = gridGenDict['continents']
        self._dataWrapModulo = gridGenDict['wrap']
        geo = gridGenDict['geo']

        if geo is not None:
            newv = vtk.vtkDoubleArray()
            newv.SetNumberOfComponents(3)
            newv.InsertTupleValue(0, [lon.min(), lat.min(), 0])
            newv.InsertTupleValue(1, [lon.max(), lat.max(), 0])

            vcs2vtk.projectArray(newv, projection, [xm, xM, ym, yM])
            dimMin = [0, 0, 0]
            dimMax = [0, 0, 0]

            newv.GetTupleValue(0, dimMin)
            newv.GetTupleValue(1, dimMax)

            maxDimX = max(dimMin[0], dimMax[0])
            maxDimY = max(dimMin[1], dimMax[1])

            if lat.max() != 0.0:
                scale = abs((maxDimY / lat.max()))

            if lon.max() != 0.0:
                temp = abs((maxDimX / lon.max()))
                if scale < temp:
                    scale = temp
        else:
            scale = 1.0

        returned["vtk_backend_grid"] = grid
        returned["vtk_backend_geo"] = geo
        missingMapper = vcs2vtk.putMaskOnVTKGrid(data1, grid, None, False,
                                                 deep=False)

        # None/False are for color and cellData
        # (sent to vcs2vtk.putMaskOnVTKGrid)
        returned["vtk_backend_missing_mapper"] = (missingMapper, None, False)

        w = vcs2vtk.generateVectorArray(data1, data2, grid)

        grid.GetPointData().AddArray(w)

        # Vector attempt
        l = self._gm.line
        if l is None:
            l = "default"
        try:
            l = vcs.getline(l)
            lwidth = l.width[0]  # noqa
            lcolor = l.color[0]
            lstyle = l.type[0]  # noqa
        except:
            lstyle = "solid"  # noqa
            lwidth = 1.  # noqa
            lcolor = 0
        if self._gm.linewidth is not None:
            lwidth = self._gm.linewidth  # noqa
        if self._gm.linecolor is not None:
            lcolor = self._gm.linecolor

        arrow = vtk.vtkGlyphSource2D()
        arrow.SetGlyphTypeToArrow()
        arrow.SetOutputPointsPrecision(vtk.vtkAlgorithm.DOUBLE_PRECISION)
        arrow.FilledOff()

        glyphFilter = vtk.vtkGlyph2D()
        glyphFilter.SetInputData(grid)
        glyphFilter.SetInputArrayToProcess(1, 0, 0, 0, "vectors")
        glyphFilter.SetSourceConnection(arrow.GetOutputPort())
        glyphFilter.SetVectorModeToUseVector()

        # Rotate arrows to match vector data:
        glyphFilter.OrientOn()

        # Scale to vector magnitude:
        glyphFilter.SetScaleModeToScaleByVector()
        glyphFilter.SetScaleFactor(scale * 2.0 * self._gm.scale)

        # These are some unfortunately named methods. It does *not* clamp the
        # scale range to [min, max], but rather remaps the range
        # [min, max] --> [0, 1].
        glyphFilter.ClampingOn()
        glyphFilter.SetRange(0.01, 1.0)

        mapper = vtk.vtkPolyDataMapper()

        glyphFilter.Update()
        data = glyphFilter.GetOutput()

        mapper.SetInputData(data)
        mapper.ScalarVisibilityOff()
        act = vtk.vtkActor()
        act.SetMapper(mapper)

        cmap = self.getColorMap()
        r, g, b, a = cmap.index[lcolor]
        act.GetProperty().SetColor(r / 100., g / 100., b / 100.)

        x1, x2, y1, y2 = vcs2vtk.getBoundsForPlotting(
            vcs.utils.getworldcoordinates(self._gm,
                                          data1.getAxis(-1),
                                          data1.getAxis(-2)),
            [xm, xM, ym, yM], self._dataWrapModulo)
        if geo is None:
            wc = [x1, x2, y1, y2]
        else:
            xrange = list(act.GetXRange())
            yrange = list(act.GetYRange())
            wc = [xrange[0], xrange[1], yrange[0], yrange[1]]

        vp = [tmpl.data.x1, tmpl.data.x2, tmpl.data.y1, tmpl.data.y2]
        # look for previous dataset_bounds different than ours and
        # modify the viewport so that the datasets are alligned
        if geo is None:
            for dp in vcs.elements['display'].values():
                if (hasattr(dp, 'backend')):
                    prevWc = dp.backend.get('dataset_bounds', None)
                    if (prevWc):
                        middleX = float(vp[0] + vp[1]) / 2.0
                        middleY = float(vp[2] + vp[3]) / 2.0
                        sideX = float(vp[1] - vp[0]) / 2.0
                        sideY = float(vp[3] - vp[2]) / 2.0
                        ratioX = float(prevWc[1] - prevWc[0]) / float(wc[1] - wc[0])
                        ratioY = float(prevWc[3] - prevWc[2]) / float(wc[3] - wc[2])
                        sideX = sideX / ratioX
                        sideY = sideY / ratioY
                        vp = [middleX - sideX, middleX + sideX, middleY - sideY, middleY + sideY]

        self._context().fitToViewportBounds(act, vp,
                                            wc=wc,
                                            priority=tmpl.data.priority,
                                            create_renderer=True)
        bounds = [min(xm, xM), max(xm, xM), min(ym, yM), max(ym, yM)]
        returned.update(self._context().renderTemplate(
            tmpl, data1,
            self._gm, taxis, zaxis,
            vtk_backend_grid=grid,
            dataset_bounds=bounds,
            plotting_dataset_bounds=[x1, x2, y1, y2],
            dataset_viewport=vp))

        if self._context().canvas._continents is None:
            continents = False
        if continents:
            self._context().plotContinents(x1, x2, y1, y2, projection,
                                           self._dataWrapModulo, vp, tmpl.data.priority,
                                           vtk_backend_grid=grid,
                                           dataset_bounds=bounds)

        returned["vtk_backend_actors"] = [[act, [x1, x2, y1, y2]]]
        returned["vtk_backend_glyphfilters"] = [glyphFilter]
        returned["vtk_backend_luts"] = [[None, None]]

        return returned
