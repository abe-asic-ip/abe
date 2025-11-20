# SPDX-FileCopyrightText: 2025 Hugh Walsh
#
# SPDX-License-Identifier: MIT

# This file: typings/pyuvm/__init__.pyi

# pylint: disable=unused-argument

"""Type stubs for pyuvm."""

from typing import Any, Callable, Generic, Optional, Type, TypeVar

T = TypeVar("T")
OT = TypeVar("OT", bound="uvm_object")
CT = TypeVar("CT", bound="uvm_component")
TT = TypeVar("TT", bound="uvm_test")

def uvm_config_db() -> Any:
    """uvm_config_db"""

def uvm_factory() -> "UVMFactory":
    """uvm_factory"""

def test(
    *,
    expect_error: Any | None = ...,
    timeout_time: int | float | None = ...,
    timeout_unit: str | None = ...,
    skip: bool = ...,
) -> Callable[[type[TT]], type[TT]]:
    """test"""

class uvm_object:  # pylint: disable=invalid-name disable=too-few-public-methods
    """uvm_object"""

    def __init__(self, name: str = ...) -> None: ...

class uvm_component:  # pylint: disable=invalid-name
    """uvm_component"""

    def __init__(self, name: str, parent: "uvm_component | None" = ...) -> None: ...
    def get_full_name(self) -> str:
        """get_full_name"""

    @property
    def name(self) -> str:
        """name"""

    def build_phase(self) -> None:
        """build_phase"""

    def connect_phase(self) -> None:
        """connect_phase"""

    def end_of_elaboration_phase(self) -> None:
        """end_of_elaboration_phase"""

    def start_of_simulation_phase(self) -> None:
        """start_of_simulation_phase"""

    async def run_phase(self) -> None:
        """run_phase"""

    def report_phase(self) -> None:
        """report_phase"""

    def final_phase(self) -> None:
        """final_phase"""

    def raise_objection(self) -> None:
        """raise_objection"""

    def drop_objection(self) -> None:
        """drop_objection"""

    @property
    def logger(self) -> Any:
        """logger"""

    def set_logging_level(self, logging_level: int) -> None:
        """set_logging_level"""

    def set_logging_level_hier(self, logging_level: int) -> None:
        """set_logging_level_hier"""

class ConfigDB:  # pylint: disable=too-few-public-methods
    """ConfigDB"""

class uvm_analysis_port(Generic[T]):  # pylint: disable=invalid-name
    """uvm_analysis_port"""

    def __init__(self, name: str, parent: uvm_component) -> None: ...
    def write(self, datum: T) -> None:
        """write"""

    def connect(self, export: Any) -> None:
        """connect"""

class uvm_analysis_export(  # pylint: disable=invalid-name disable=too-few-public-methods
    Generic[T]
):
    """uvm_analysis_export"""

    def __init__(self, name: str, parent: uvm_component) -> None: ...
    def connect(self, provider: Any) -> None:
        """connect"""

class uvm_tlm_analysis_fifo(Generic[T], uvm_component):  # pylint: disable=invalid-name
    """uvm_tlm_analysis_fifo"""

    analysis_export: Any

    def __init__(  # pylint: disable=super-init-not-called
        self, name: str, parent: uvm_component
    ) -> None: ...
    async def get(self) -> T:
        """get"""

    def write(self, item: T) -> None:
        """write"""

    def put(self, item: T) -> None:
        """put"""

class uvm_driver(Generic[T], uvm_component):  # pylint: disable=invalid-name
    """uvm_driver"""

    seq_item_port: Any

class uvm_monitor(Generic[T], uvm_component):  # pylint: disable=invalid-name
    """uvm_monitor"""

class uvm_agent(uvm_component):  # pylint: disable=invalid-name
    """uvm_agent"""

    is_active: "uvm_active_passive_enum"

class uvm_scoreboard(uvm_component):  # pylint: disable=invalid-name
    """uvm_scoreboard"""

class uvm_subscriber(uvm_component, Generic[T]):  # pylint: disable=invalid-name
    """uvm_subscriber"""

    analysis_export: Any

    def __init__(  # pylint: disable=super-init-not-called
        self, name: str, parent: uvm_component | None
    ) -> None: ...
    def write(self, tt: T) -> None:
        """write"""

class uvm_env(uvm_component):  # pylint: disable=invalid-name
    """uvm_env"""

class uvm_sequence_item(  # pylint: disable=invalid-name disable=too-few-public-methods
    uvm_object
):
    """uvm_sequence_item"""

SI = TypeVar("SI", bound=uvm_sequence_item)

class uvm_sequencer(uvm_component):  # pylint: disable=invalid-name
    """uvm_sequencer"""

    seq_item_export: Any

class uvm_sequence(Generic[SI], uvm_object):  # pylint: disable=invalid-name
    """uvm_sequence"""

    async def body(self) -> None:
        """body"""

    async def start_item(self, item: SI) -> None:
        """start_item"""

    async def finish_item(self, item: SI) -> None:
        """finish_item"""

    async def start(self, seqr: "uvm_sequencer", call_pre_post: bool = True) -> None:
        """start"""

class UVMFactory:
    """UVMFactory"""

    def create_component_by_type(
        self,
        requested_type: Type[CT],
        parent_inst_path: str = "",
        name: str = "",
        parent: uvm_component | None = None,
    ) -> CT:
        """create_component_by_type"""

    def create_object_by_type(
        self, requested_type_name: Type[OT], parent_inst_path: str = "", name: str = ""
    ) -> OT:
        """create_object_by_type"""

    def set_type_override_by_type(
        self, original_type: Any, override_type: Any, replace: bool = True
    ) -> None:
        """set_type_override_by_type"""

    def set_type_override_by_name(
        self, original_type_name: str, override_type_name: str, replace: bool = True
    ) -> None:
        """set_type_override_by_name"""

    def set_inst_override_by_type(
        self, original_type: Any, override_type: Any, full_inst_path: str
    ) -> None:
        """set_inst_override_by_type"""

    def set_inst_override_by_name(
        self, original_type_name: str, override_type_name: str, full_inst_path: str
    ) -> None:
        """set_inst_override_by_name"""

    def print(self, debug_level: int = 1) -> None:
        """print"""

class uvm_test(uvm_component):  # pylint: disable=invalid-name
    """uvm_test"""

class uvm_active_passive_enum:  # pylint: disable=invalid-name disable=too-few-public-methods
    """uvm_active_passive_enum"""

    UVM_ACTIVE: "uvm_active_passive_enum"
    UVM_PASSIVE: "uvm_active_passive_enum"
