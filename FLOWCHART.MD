```mermaid
flowchart TD

    %% ========= START =========
    A0([Start / Choose Task])

    A0 --> B0[Quick Validation<br/>validate.py]
    A0 --> C0[Core UE Solve<br/>network.py]
    A0 --> D0[Policy Analysis<br/>policies.modifiers + experiments]
    A0 --> E0[Advanced Testing & Benchmarking<br/>tests/*.py]

    %% ========= QUICK VALIDATION =========
    subgraph S1[Quick Validation (validate.py)]
        B0 --> B1[Parse CLI args<br/>(net-file, trips-file, --skip-tests, --runs)]
        B1 --> B2{Skip unit tests?}
        B2 -- "No" --> B3[Run tests.py / grader.py<br/>unit tests]
        B2 -- "Yes" --> B4[Construct Network<br/>Network(net_file, trips_file)]
        B3 --> B4

        B4 --> B5[Run net.userEquilibrium()<br/>(FW or MSA)]
        B5 --> B6[Collect convergence data<br/>relative_gaps, iteration_times]
        B6 --> B7[Export flows & metrics<br/>to outputs/*_ue_flows.txt, CSV]
    end

    %% ========= CORE UE SOLVE =========
    subgraph S2[Core UE Solve (network.py)]
        C0 --> C1[Import Network, link, node, od, utils]
        C1 --> C2[Load TNTP files<br/>Network(net_file, trips_file)]
        C2 --> C3[Call userEquilibrium(stepSizeRule, maxIterations,<br/>targetGap, gapFunction, stepType)]

        C3 --> C4[Shortest path + AON assignment<br/>(per origin)]
        C4 --> C5[Flow shifting / FW step size<br/>shiftFlows, FrankWolfeStepSize]
        C5 --> C6[Update link flows & costs<br/>BPR functions]

        C6 --> C7[Compute gap<br/>relativeGap() or averageExcessCost()]
        C7 --> C8{Gap ≤ targetGap<br/>or maxIterations reached?}
        C8 -- "No" --> C3
        C8 -- "Yes" --> C9[Finalize solution<br/>store convergence history]
        C9 --> C10[Inspect results<br/>per-link flow/cost, TSTT, metrics]
    end

    %% ========= POLICY ANALYSIS =========
    subgraph S3[Policy Analysis (policies.modifiers + experiments)]
        D0 --> D1[Load base Network<br/>(e.g., SiouxFalls)]
        D1 --> D2[Apply modifiers<br/>scale_capacity, scale_demand,<br/>remove_links, reset_flows]
        D2 --> D3[Re-run net.userEquilibrium()<br/>under policy scenario]
        D3 --> D4[Compute metrics via get_metrics()<br/>TSTT, relative_gap, etc.]
        D4 --> D5[Compare baseline vs policy<br/>before/after metrics]
    end

    %% ========= ADVANCED TESTING =========
    subgraph S4[Advanced Testing & Benchmarking (tests/)]
        E0 --> E1[Select protocol file(s)<br/>tests/protocol/*.txt]
        E1 --> E2[Run tests/run_protocol.py<br/>(mode: auto/fwstep/shift/ue_solve)]
        E1 --> E3[OR run tests/run_protocol_per_run.py<br/>for per-run logging]

        E2 --> E4[Per-protocol loop:<br/>load Network, run UE / metric eval,<br/>repeat for --runs]
        E3 --> E4

        E4 --> E5[Aggregate stats or keep per-run data<br/>CSV/JSON, optional cProfile]
        E5 --> E6[Optional comparison tools:<br/>compare_networks.py, compare_results.py]
    end
