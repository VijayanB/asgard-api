from collections import defaultdict
from decimal import Decimal
from typing import Dict, List, Set

from asgard.backends.mesos.models.app import MesosApp
from asgard.backends.mesos.models.task import MesosTask
from asgard.http.client import HttpClient
from asgard.math import round_up
from asgard.models.agent import Agent

_http_client = HttpClient()


class MesosAgent(Agent):
    type: str = "MESOS"

    def filter_by_attrs(self, kv):
        pass

    async def calculate_stats(self):
        """
        Calculate usage statistics.
            - CPU % usage
            - RAM % usage
        """
        cpu_pct = (
            Decimal(self.used_resources["cpus"])
            / Decimal(self.resources["cpus"])
            * 100
        )

        ram_pct = (
            Decimal(self.used_resources["mem"])
            / Decimal(self.resources["mem"])
            * 100
        )

        self.stats = {
            "cpu_pct": str(round_up(cpu_pct)),
            "ram_pct": str(round_up(ram_pct)),
        }

    async def apps(self) -> List[MesosApp]:  # type: ignore
        self_address = f"http://{self.hostname}:{self.port}"
        containers_url = f"{self_address}/containers"
        apps = []
        response = await _http_client.get(containers_url)

        data = await response.json()
        all_apps: Set[str] = set()
        for container_info in data:
            app_id = MesosApp.transform_to_asgard_app_id(
                container_info["executor_id"]
            )
            if app_id not in all_apps:
                apps.append(MesosApp(**{"id": app_id}))
                all_apps.add(app_id)
        return apps

    async def tasks(self, app_id: str) -> List[MesosTask]:
        self_address = f"http://{self.hostname}:{self.port}"
        containers_url = f"{self_address}/containers"
        response = await _http_client.get(containers_url)
        data = await response.json()
        tasks_per_app: Dict[str, List[MesosTask]] = defaultdict(list)
        for container_info in data:
            app_id_ = MesosApp.transform_to_asgard_app_id(
                container_info["executor_id"]
            )
            tasks_per_app[app_id_].append(
                MesosTask(
                    **{
                        "name": MesosTask.transform_to_asgard_task_id(
                            container_info["executor_id"]
                        )
                    }
                )
            )
        return tasks_per_app[app_id]
