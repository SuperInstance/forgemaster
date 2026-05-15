package main

import (
	"fmt"
	"math"
	"math/rand"
	"time"
)

func eisensteinNorm(a, b int64) int64 {
	return a*a - a*b + b*b
}

type IntPair struct {
	A, B int64
}

func eisensteinSnap(x, y float64) IntPair {
	q := (2.0/3.0*x - 1.0/3.0*y)
	r := (2.0 / 3.0 * y)
	rq := math.Round(q)
	rr := math.Round(r)
	rs := math.Round(-q - r)
	diff := math.Abs(rq + rr + rs)
	if diff == 2.0 {
		if math.Abs(rq-q) > math.Abs(rr-r) {
			rq = -rr - rs
		} else {
			rr = -rq - rs
		}
	}
	return IntPair{int64(rq), int64(rr)}
}

func constraintCheck(a, b int64, radius float64) bool {
	return float64(eisensteinNorm(a, b)) <= radius*radius
}

const N = 10_000_000

func main() {
	rng := rand.New(rand.NewSource(42))

	normA := make([]int64, N)
	normB := make([]int64, N)
	snapX := make([]float64, N)
	snapY := make([]float64, N)
	conA := make([]int64, N)
	conB := make([]int64, N)
	conR := make([]float64, N)

	for i := 0; i < N; i++ {
		normA[i] = rng.Int63n(2001) - 1000
		normB[i] = rng.Int63n(2001) - 1000
		snapX[i] = rng.Float64()*200.0 - 100.0
		snapY[i] = rng.Float64()*200.0 - 100.0
		conA[i] = rng.Int63n(201) - 100
		conB[i] = rng.Int63n(201) - 100
		conR[i] = rng.Float64()*49.0 + 1.0
	}

	// Benchmark norm
	var normSum int64
	start := time.Now()
	for i := 0; i < N; i++ {
		normSum += eisensteinNorm(normA[i], normB[i])
	}
	normTime := time.Since(start).Seconds()

	// Benchmark snap
	var snapFirst IntPair
	start = time.Now()
	for i := 0; i < N; i++ {
		s := eisensteinSnap(snapX[i], snapY[i])
		if i == 0 {
			snapFirst = s
		}
	}
	snapTime := time.Since(start).Seconds()

	// Benchmark constraint
	var conPass int64
	start = time.Now()
	for i := 0; i < N; i++ {
		if constraintCheck(conA[i], conB[i], conR[i]) {
			conPass++
		}
	}
	conTime := time.Since(start).Seconds()

	fmt.Printf("Go Results (N=%d):\n", N)
	fmt.Printf("  eisenstein_norm:  %.3fs  (sum=%d)\n", normTime, normSum)
	fmt.Printf("  eisenstein_snap:  %.3fs  (first=(%d,%d))\n", snapTime, snapFirst.A, snapFirst.B)
	fmt.Printf("  constraint_check: %.3fs  (pass=%d)\n", conTime, conPass)
	fmt.Printf("  TOTAL: %.3fs\n", normTime+snapTime+conTime)
}
