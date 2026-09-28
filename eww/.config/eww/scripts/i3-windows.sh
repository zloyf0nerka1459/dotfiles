#!/usr/bin/env bash

emit_windows() {
    i3-msg -t get_tree 2>/dev/null | jq -c '
        def walk_nodes($workspace):
            . as $node
            | if $node.type == "workspace" then
                reduce ($node.nodes[]?, $node.floating_nodes[]?) as $child
                    ([]; . + ($child | walk_nodes($node.name)))
              elif ($node.window != null) then
                [{
                    id: $node.id,
                    title: ($node.name // $node.window_properties.class // "Untitled"),
                    workspace: $workspace,
                    focused: ($node.focused // false),
                    urgent: ($node.urgent // false)
                }]
              else
                reduce ($node.nodes[]?, $node.floating_nodes[]?) as $child
                    ([]; . + ($child | walk_nodes($workspace)))
              end;

        walk_nodes("")
        | map(select(.workspace != "" and .workspace != "__i3_scratch"))
        | map({
            id: .id,
            title: (if (.title | length) > 28 then (.title[0:25] + "...") else .title end),
            workspace: .workspace,
            focused: .focused,
            urgent: .urgent,
            prefix: (if .focused then ("[* " + .workspace + "]") elif .urgent then ("[! " + .workspace + "]") else ("[" + .workspace + "]") end)
        })
    ' 2>/dev/null || echo "[]"
}

emit_windows
i3-msg -t subscribe -m '[ "window", "workspace" ]' 2>/dev/null | while read -r _; do
    emit_windows
done
