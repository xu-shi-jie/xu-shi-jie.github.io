---
title: $k$-means algorithm
author: Shijie Xu
date: 2024/12/02
copyright: CC BY-NC-SA 4.0
---

## Introduction
$k$-means is a simple yet powerful clustering algorithm that takes $n$ vectors $v_i\in\mathbb{R}^m,i=1,\ldots,n$ as input, and output the $k$ clusters $c_i,i=1,\ldots,k$, which attempts to minimize the target function: $$ \sum_{i=1}^n (v_i-c_{l_i})^2 $$ where $l_i$ represents that $x_i$ belongs to the $l_i$-th cluster.

The algorithm runs by starting with $k$ randomly chosen points as initial centers.
