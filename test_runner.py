# Copyright (c) Meta Platforms, Inc. and affiliates.
# This software may be used and distributed according to the terms of the Llama 2 Community License Agreement.

# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
import os
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from typing import Sequence

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


@dataclass
class OverrideDefinitions:
    """
    This class is used to define the override definitions for the integration tests.
    """

    override_args: Sequence[Sequence[str]] = tuple(tuple(" "))
    test_descr: str = "default"


CONFIG_DIR = "./train_configs"
test_checkpoint_dir = "./test_runner_checkpoint"

"""
key is the config file name and value is a list of OverrideDefinitions
that is used to generate variations of integration tests based on the
same root config file.
"""
integration_tests_flavors = defaultdict(list)
integration_tests_flavors["debug_model.toml"] = [
    OverrideDefinitions(
        [
            ["--training.compile"],
        ],
        "1D compile",
    ),
    OverrideDefinitions(
        [
            ["--training.tensor_parallel_degree 2 --model.norm_type=rmsnorm"],
        ],
        "Eager mode 2DParallel",
    ),
    OverrideDefinitions(
        [
            [f"--checkpoint.folder {test_checkpoint_dir}"],
            [f"--checkpoint.folder {test_checkpoint_dir}", "--training.steps 20"],
        ],
        "Checkpoint Integration Test",
    ),
]


def run_test(test_flavor: OverrideDefinitions, full_path: str):
    # run_test supports sequence of tests.
    for override_arg in test_flavor.override_args:
        cmd = f"CONFIG_FILE={full_path} NGPU=4 ./run_llama_train.sh"
        if override_arg:
            cmd += " " + " ".join(override_arg)
        print(
            f"=====Integration test, flavor : {test_flavor.test_descr}, command : {cmd}====="
        )
        result = subprocess.run(
            [cmd],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=True,
        )
        print(result.stdout)
        if result.returncode != 0:
            raise Exception(
                f"Integration test failed, flavor : {test_flavor.test_descr}, command : {cmd}"
            )


for config_file in os.listdir(CONFIG_DIR):
    if config_file.endswith(".toml"):
        full_path = os.path.join(CONFIG_DIR, config_file)
        with open(full_path, "rb") as f:
            config = tomllib.load(f)
            is_integration_test = config["job"].get("use_for_integration_test", False)
            if is_integration_test:
                test_flavors = [OverrideDefinitions()] + integration_tests_flavors[
                    config_file
                ]

                for test_flavor in test_flavors:
                    run_test(test_flavor, full_path)