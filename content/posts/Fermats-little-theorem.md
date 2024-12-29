---
date: '2008-12-03T10:35:57+09:00'
draft: false
title: Proof of Fermat's little theorem
comments: true
---

*Fermat's little theorem* states that for all primes $p$ and integers $a$, $a^p\equiv a\mod p$.

It is easy to verify that the theorem holds when $p=2$, since $a^2-a\equiv a(a-1)\equiv 0\mod 2$. To prove the theorem, it suffices to consider only the case $a\ge 0$, because $(-a)^p\equiv -a^p\equiv -a\mod p$ holds whenever the theorem is valid for $a>0$.

The theorem is trivially true for $a=0$. Assuming it holds for $a$, we aim to prove it for $a+1$. By induction, the theorem will then be established.

Using the Binomial theorem, we expand: $$(a+1)^p=\sum_{i=0}^p{p\choose i}a^i=\sum_{i=0}^p\frac{p!}{i!(p-i)!}a^i.$$

For $0 < i < p$, each term in the sum includes a factor of $p$, because $p$ is prime and $i!(p-i)!$ does not contain $p$ as a factor. Thus, modulo $p$, the sum simplifies to: $$(a+1)^p\equiv {p\choose p}a^p+{p\choose 0}a^0\equiv a^p+1\equiv a+1\mod p.$$

In the last step, we used the assumption that the theorem holds for $a$.