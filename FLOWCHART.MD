```mermaid
flowchart TD

    %% ========= START =========
    A0([Start / Choose Task])

    A0 --> B0[Quick Validation - validate.py]
    A0 --> C0[Core UE Solve - network.py]
    A0 --> D0[Policy Analysis - policies]
    A0 --> E0[Advanced Testing and Benchmarking - tests]

    %% ========= QUICK VALIDATION =========
    subgraph S1[Quick Validation - validate.py]
        B0 --> B1[Parse CLI args]
        B1 --> B2{Skip unit tests?}
        B2 -- No --> B3[Run unit tests]
        B2 -- Yes --> B4[Construct Network from TNTP files]
        B3 --> B4
        B4 --> B5[Run net.userEquilibrium]
        B5 --> B6[Collect convergence data]
        B6 --> B7[Export flows and metrics]
    end

    %% ========= CORE UE SOLVE =========
    subgraph S2[Core UE Solve - network.py]
        C0 --> C1[Import classes and modules]
        C1 --> C2[Load TNTP network and demand files]
        C2 --> C3[Call userEquilibrium with parameters]
        C3 --> C4[Shortest path and all or nothing assignment]
        C4 --> C5[Flow shifting and Frank Wolfe step size]
        C5 --> C6[Update link flows and costs]
        C6 --> C7[Compute gap metric]
        C7 --> C8{Converged or max iterations?}
        C8 -- No --> C3
        C8 -- Yes --> C9[Finalize solution]
        C9 --> C10[Inspect results and metrics]
    end

    %% ========= POLICY ANALYSIS =========
    subgraph S3[Policy Analysis - policies and experiments]
        D0 --> D1[Load base Network]
        D1 --> D2[Apply modifiers to capacity demand or links]
        D2 --> D3[Re run userEquilibrium]
        D3 --> D4[Compute metrics with get_metrics]
        D4 --> D5[Compare baseline and policy results]
    end

    %% ========= ADVANCED TESTING =========
    subgraph S4[Advanced Testing and Benchmarking - tests]
        E0 --> E1[Select protocol files]
        E1 --> E2[Run tests run_protocol]
        E1 --> E3[Or run tests run_protocol_per_run]
        E2 --> E4[Loop over runs and evaluate network]
        E3 --> E4
        E4 --> E5[Aggregate or log statistics]
        E5 --> E6[Optional compare_networks and compare_results]
    end
