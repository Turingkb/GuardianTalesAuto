"""Read independently overridden fields from the current task context."""


def resolve_task_settings(screen, params: dict | None) -> dict:
    # MaaFramework exports an omitted custom_action_param as JSON null.
    if params is None:
        return {}
    if "settings_node" not in params:
        return params
    result = dict(params)
    node = result.pop("settings_node")
    fields = result.pop("settings_fields")
    for field in fields:
        data = screen.node_data(node + "_Setting_" + field)
        result[field] = data["action"]["param"]["custom_action_param"][field]
    return result
