#!/bin/bash
# Devflow Bash Tab Completion
#
# Installation:
# 1. Source in ~/.bashrc:
#    source /path/to/devflow/tooling/completions/run-story-completion.bash
#
# 2. Or copy to system completions:
#    cp run-story-completion.bash /etc/bash_completion.d/devflow

# Available agents
_devflow_agents="SM DEV BA ARCHITECT PM WRITER MAINTAINER REVIEWER"

# Available models
_devflow_models="opus sonnet haiku"

# Collaboration modes
_devflow_modes="swarm pair auto-route sequential"

# run-story.sh completion
_run_story_completion() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    # Main options
    opts="--swarm --pair --auto-route --sequential --agents --max-iterations --model --budget --memory --query --route-only --quiet --debug --dry-run --help"

    case "${prev}" in
        --agents|-a)
            # Support comma-separated agent completion
            local existing_agents current_part
            if [[ "$cur" == *,* ]]; then
                existing_agents="${cur%,*},"
                current_part="${cur##*,}"
            else
                existing_agents=""
                current_part="$cur"
            fi

            local suggestions=""
            for agent in $_devflow_agents; do
                if [[ "$agent" == ${current_part}* ]]; then
                    suggestions="$suggestions ${existing_agents}${agent}"
                fi
            done
            COMPREPLY=( $(compgen -W "$suggestions" -- "") )
            return 0
            ;;
        --model|-m)
            COMPREPLY=( $(compgen -W "${_devflow_models}" -- "${cur}") )
            return 0
            ;;
        --max-iterations|--max-iter)
            COMPREPLY=( $(compgen -W "1 2 3 4 5 10" -- "${cur}") )
            return 0
            ;;
        --budget)
            COMPREPLY=( $(compgen -W "5.0 10.0 20.0 50.0 100.0" -- "${cur}") )
            return 0
            ;;
        --query)
            # No specific completions for query text
            return 0
            ;;
        *)
            ;;
    esac

    # Complete options
    if [[ ${cur} == -* ]]; then
        COMPREPLY=( $(compgen -W "${opts}" -- "${cur}") )
        return 0
    fi
}

# run-collab.py completion
_run_collab_completion() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    opts="--swarm --pair --auto --sequential --agents --max-iterations --model --budget --memory --query --route-only --quiet --help"

    case "${prev}" in
        --agents)
            local existing_agents current_part
            if [[ "$cur" == *,* ]]; then
                existing_agents="${cur%,*},"
                current_part="${cur##*,}"
            else
                existing_agents=""
                current_part="$cur"
            fi

            local suggestions=""
            for agent in $_devflow_agents; do
                if [[ "$agent" == ${current_part}* ]]; then
                    suggestions="$suggestions ${existing_agents}${agent}"
                fi
            done
            COMPREPLY=( $(compgen -W "$suggestions" -- "") )
            return 0
            ;;
        --model)
            COMPREPLY=( $(compgen -W "${_devflow_models}" -- "${cur}") )
            return 0
            ;;
        --max-iterations)
            COMPREPLY=( $(compgen -W "1 2 3 4 5 10" -- "${cur}") )
            return 0
            ;;
        --budget)
            COMPREPLY=( $(compgen -W "5.0 10.0 20.0 50.0 100.0" -- "${cur}") )
            return 0
            ;;
        *)
            ;;
    esac

    if [[ ${cur} == -* ]]; then
        COMPREPLY=( $(compgen -W "${opts}" -- "${cur}") )
        return 0
    fi
}

# Register completions
complete -F _run_story_completion run-story.sh
complete -F _run_story_completion run-story
complete -F _run_collab_completion run-collab.py
complete -F _run_collab_completion run-collab
complete -F _run_collab_completion python3 run-collab.py

echo "Devflow bash completion loaded."
