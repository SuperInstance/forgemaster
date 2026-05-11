# SNAPKIT-V2-TLDR.md

## The 10 Clunky Joints & Their Fixes

```
Joint                Problem                              Fix
──────────────────────────────────────────────────────────────────────
1. 9 channels        Arbitrary list                       D₅ × A₁ × Affine(3) = 9
2. Single tolerance  1D thinking                          Riemannian metric tensor g_{ij}
3. Script matching   Cosine (no magnitude)                Eisenstein/lattice distance
4. Learning flat     No topology awareness                Per-lattice script pools
5. Single scale      One timescale                        Hierarchical snap (RG flow)
6. Budget flat       Starvation risk                      Hierarchical pools (safety/ops/explore)
7. Output one-size   Embedded pays full cost              Profile-driven projection
8. Single topology   Wrong for mixed-modal                LatticeMesh (cell complex)
9. Linear pipeline   No branching/feedback                DAGPipeline (graph, conditional edges)
10. No distribution  Single-machine ceiling               Partition-of-unity sheaf gluing
```

## Why Each Fix Is Grounded

| Fix | Math Grounding | Equivalent Theorem |
|-----|---------------|-------------------|
| D₅ × A₁ × Affine(3) | Affine Lie algebra | D₅^∧ has 9 = 5+1+3 |
| TensorTolerance | Riemannian metric g_{ij} | ds² = g_{ij}dxⁱdxʲ + Cartan constraint |
| Script distance | Lattice norm ∥·∥_Λ | ∥x-y∥_Λ where Λ is the snap lattice |
| Lattice pools | Graded ring | Hom(S_i, S_j) = 0 for i≠j |
| RG-flow snap | Renormalization group | L_{k+1} coarse-grains L_k |
| Pool hierarchy | D₅ α₁ is the fork | D₅ has one "long root" with priority |
| Output projectors | π: DataBundle → Subspace | MINIMAL = π_{snap}, RESEARCH = id |
| LatticeMesh | Sheaf over cell complex | H¹ = 0 ↔ gluing consistent |
| DAGPipeline | Constraint dependency graph | DAG is the constraint graph |
| Partition-of-unity | Sheaf cohomology H¹ | ∥partition δ∥ → 0 as halo → 0 |

## v2 Core Philosophy

> **v1**: "What can I safely ignore?"  
> **v2**: "What can each part of the system safely ignore, at what scale, in what topology, with what precision?"

## Sprint Plan (4 Weeks)

1. **Week 1**: Core — TensorTolerance, snap v2, LatticeAwareScript, topology-tagged learning
2. **Week 2**: Structure — DAGPipeline, HierarchicalSnap, HierarchicalAttention, output profiles
3. **Week 3**: Mesh — LatticeMesh, DistributedSnapPartition, SheafGluing
4. **Week 4**: Integration — Migration script, C/CUDA bindings, docs, domain profiles
