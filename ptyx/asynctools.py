import asyncio

Command = list[str]


async def _run_command(command: Command) -> tuple[str, str]:
    proc = await asyncio.create_subprocess_exec(
        *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    return (stdout.decode().strip(), stderr.decode().strip())


async def _gather(commands: list[Command]):
    tasks = [asyncio.create_task(_run_command(command)) for command in commands]
    results = await asyncio.gather(*tasks)
    output_list = []
    for result in results:
        output_list.append(result[0])
    return output_list


def run_commands(commands: list[Command]) -> list[str]:
    return asyncio.run(_gather(commands))
