import asyncio

Command = list[str]


async def _run_command(command: Command, shell=False) -> tuple[str, str]:
    if shell:
        proc = await asyncio.create_subprocess_shell(
            " ".join(command), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
    else:
        proc = await asyncio.create_subprocess_exec(
            *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
    stdout, stderr = await proc.communicate()
    return stdout.decode().strip(), stderr.decode().strip()


async def _gather(commands: list[Command], shell=False):
    tasks = [asyncio.create_task(_run_command(command, shell)) for command in commands]
    results = await asyncio.gather(*tasks)
    output_list = []
    for result in results:
        output_list.append(result[0])
    return output_list


def run_commands(commands: list[Command], shell=False, max_processes=None) -> list[str]:
    """Run commands asynchronously. The number of processes may be limited using `max_processes`."""
    if max_processes is None:
        max_processes = len(commands)
    packs = [commands[i : i + max_processes] for i in range(0, len(commands), max_processes)]
    return sum((asyncio.run(_gather(pack, shell)) for pack in packs), start=[])
