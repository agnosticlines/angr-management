from typing import TYPE_CHECKING, Any, Optional, Sequence

from PySide6.QtCore import QAbstractTableModel, QSize, Qt
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QMenu, QTableView, QVBoxLayout

from angrmanagement.data.breakpoint import Breakpoint, BreakpointManager, BreakpointType
from angrmanagement.ui.dialogs import BreakpointDialog

from .view import BaseView

if TYPE_CHECKING:
    import PySide6

    from angrmanagement.ui.workspace import Workspace


class QBreakpointTableModel(QAbstractTableModel):
    """
    Breakpoint table model.
    """

    Headers = ["Type", "Address", "Size", "Comment"]
    COL_TYPE = 0
    COL_ADDR = 1
    COL_SIZE = 2
    COL_COMMENT = 3

    def __init__(self, breakpoint_mgr: BreakpointManager):
        super().__init__()
        self.breakpoint_mgr = breakpoint_mgr
        self.breakpoint_mgr.breakpoints.am_subscribe(self._on_breakpoints_updated)

    def _on_breakpoints_updated(self, **kwargs):  # pylint:disable=unused-argument
        self.beginResetModel()
        self.endResetModel()

    def rowCount(self, parent: "PySide6.QtCore.QModelIndex" = ...) -> int:  # pylint:disable=unused-argument
        return len(self.breakpoint_mgr.breakpoints)

    def columnCount(self, parent: "PySide6.QtCore.QModelIndex" = ...) -> int:  # pylint:disable=unused-argument
        return len(self.Headers)

    def headerData(
        self, section: int, orientation: "PySide6.QtCore.Qt.Orientation", role: int = ...
    ) -> Any:  # pylint:disable=unused-argument
        if role != Qt.DisplayRole:
            return None
        if section < len(self.Headers):
            return self.Headers[section]
        return None

    def data(self, index: "PySide6.QtCore.QModelIndex", role: int = ...) -> Any:
        if not index.isValid():
            return None
        row = index.row()
        if row >= len(self.breakpoint_mgr.breakpoints):
            return None
        col = index.column()
        if role == Qt.DisplayRole:
            return self._get_column_text(self.breakpoint_mgr.breakpoints[row], col)
        else:
            return None

    def _get_column_text(self, bp: "Breakpoint", column: int) -> str:
        if column == self.COL_TYPE:
            return {BreakpointType.Execute: "Execute", BreakpointType.Read: "Read", BreakpointType.Write: "Write"}.get(
                bp.type
            )
        elif column == self.COL_ADDR:
            return f"{bp.addr:#08x}"
        elif column == self.COL_SIZE:
            return f"{bp.size:#x}"
        elif column == self.COL_COMMENT:
            return bp.comment
        else:
            raise AssertionError


class QBreakpointTableWidget(QTableView):
    """
    Breakpoint table widget.
    """

    def __init__(self, breakpoint_mgr: BreakpointManager, workspace: "Workspace", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.workspace = workspace
        self.breakpoint_mgr = breakpoint_mgr

        hheader = self.horizontalHeader()
        hheader.setVisible(True)

        vheader = self.verticalHeader()
        vheader.setVisible(False)
        vheader.setDefaultSectionSize(20)

        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)

        self.model: QBreakpointTableModel = QBreakpointTableModel(self.breakpoint_mgr)
        self.setModel(self.model)

        for col in range(len(QBreakpointTableModel.Headers)):
            hheader.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        hheader.setStretchLastSection(True)
        self.doubleClicked.connect(self._on_cell_double_click)

    #
    # Events
    #

    def closeEvent(self, event):
        self.model.shutdown()
        super().closeEvent(event)

    def contextMenuEvent(self, event):
        selected_rows = {i.row() for i in self.selectedIndexes()}
        breakpoints = [self.breakpoint_mgr.breakpoints[r] for r in selected_rows]
        menu = QMenu("", self)
        if len(breakpoints):
            if len(breakpoints) == 1:
                menu.addAction("Edit breakpoint", lambda: self.edit_breakpoint(breakpoints[0]))
            menu.addAction(
                "Remove breakpoint" + ("s" if len(breakpoints) > 1 else ""),
                lambda: self.remove_breakpoints(breakpoints),
            )
            menu.addSeparator()
        menu.addAction("New breakpoint", self.new_breakpoint)
        menu.exec_(event.globalPos())

    def _on_cell_double_click(self, index):
        self.edit_breakpoint(self.breakpoint_mgr.breakpoints[index.row()])

    def new_breakpoint(self):
        bp = Breakpoint(BreakpointType.Execute, 0)
        if BreakpointDialog(bp, self.workspace, self).exec_():
            self.breakpoint_mgr.add_breakpoint(bp)

    def edit_breakpoint(self, breakpoint_: Breakpoint):
        BreakpointDialog(breakpoint_, self.workspace, self).exec_()

    def remove_breakpoints(self, breakpoints: Sequence[Breakpoint]):
        for b in breakpoints:
            self.breakpoint_mgr.remove_breakpoint(b)


class BreakpointsView(BaseView):
    """
    Breakpoints table view.
    """

    def __init__(self, workspace, instance, default_docking_position, *args, **kwargs):
        super().__init__("breakpoints", workspace, instance, default_docking_position, *args, **kwargs)
        self.base_caption = "Breakpoints"
        self._tbl_widget: Optional[QBreakpointTableWidget] = None
        self._init_widgets()
        self.reload()

    def reload(self):
        pass

    @staticmethod
    def minimumSizeHint(*args, **kwargs):  # pylint:disable=unused-argument
        return QSize(200, 200)

    def _init_widgets(self):
        vlayout = QVBoxLayout()
        self._tbl_widget = QBreakpointTableWidget(self.instance.breakpoint_mgr, self.workspace)
        vlayout.addWidget(self._tbl_widget)
        self.setLayout(vlayout)
