#!/usr/bin/env python

from game import Game
from genetic_ai import Genome
import multiprocessing
import collections
import argparse
import math
import copy
import random
import time


def worker(genomes):
    start = time.time()
    try:
        g = Game(["GeneticAI" for g in genomes], [dict(name=g.name(), genome=g) for g in genomes])
        result = g.play()
    except Exception as exc:
        print("Exception raised in worker:", exc)
        result = {}
    elapsed = time.time() - start
    return elapsed, result

class Population(object):
    def __init__(self, population, generations, mutation, crossover, games, workers, players):
        self.population = population
        self.generations = generations
        self.mutation = mutation
        self.crossover = crossover
        self.games = games
        self.players = players
        self.workers = workers
        self.pool = None
        self.history = []
    
    def run(self):
        genomes = self.initialise()
        self.pool = multiprocessing.Pool(processes=self.workers)
        games_per_generation = len(genomes)*self.games/self.players
        print("%d genomes, %d rounds each, %d players per game -> %d games per generation" % (len(genomes), self.games, self.players, games_per_generation))
        for i in range(self.generations):
            genomes = self.generation(genomes)
            print("Generation:", i)
            print("Fitness: min=%(min_f).2f, max=%(max_f).2f, avg=%(avg_f).2f, stddev=%(stddev_f).2f" % self.history[-1])
            print("Time: min=%(min_t).2f, max=%(max_t).2f, avg=%(avg_t).2f, stddev=%(stddev_t).2f" % self.history[-1])
            time_left = int(self.history[-1]['avg_t'] * (self.generations - i - 1) * games_per_generation / self.workers)
            print("Time remaining: %d hour(s) %d min(s)" % (time_left / 3600, (time_left % 3600) / 60))
            print("Best individual:", self.history[-1]["best"])
        self.pool.close()
        self.pool.join()
                
    def initialise(self):
        return [Genome() for _ in range(self.population)]

    def fitness(self, genomes):
        """
        Evaluates fitness by randomly drawing players such that each
        genome plays self.games, then averaging the score over those.

        Playing against other members of the population may produce
        unwanted effects compared to playing against random players,
        but significantly reduces the number of games required for
        each generation.
        """
        src = []
        for g in genomes:
            src += [g]*self.games
        games = []
        random.shuffle(src)

        while len(src) >= self.players:
            games += [tuple(src.pop() for _ in range(self.players))]
         
        results = self.pool.map(worker, games)
        scores = collections.defaultdict(list)
        
        times = []
        for t, result in results:
            times += [t]
            for name, score in result.items():
                scores[name] += [score]
    
        fitness = {n: float(sum(s))/len(s) for n, s in scores.items()}
        f = fitness.values()
        avg_f = sum(f)/len(f)
        max_f = max(f)
        min_f = min(f)
        stddev_f = math.sqrt(sum((i-avg_f)**2 for i in f)/len(f))
        best = sorted(genomes, key=lambda x: fitness[x.name()], reverse=True)[0]
        
        avg_t = sum(times)/len(times)
        max_t = max(times)
        min_t = min(times)
        stddev_t = math.sqrt(sum((i-avg_t)**2 for i in times)/len(times))

        self.history += [dict(best=copy.deepcopy(best), avg_f=avg_f, max_f=max_f, 
                              stddev_f=stddev_f, min_f=min_f, avg_t=avg_t, 
                              min_t=min_t, max_t=max_t, stddev_t=stddev_t)]

        return fitness

    def select(self, fitness, genomes):
        """
        Performs roulette selection based on linear-scaled scores.
        """ 
        min_f = min(fitness.values())
        max_f = max(fitness.values())
        range_f = max_f - min_f
        scaled_fitness = {k: (v - min_f)/range_f for k, v in fitness.items()}
        sum_sf = sum(scaled_fitness.values())

        roulette = []
        cumulative = 0
        for k, v in scaled_fitness.items():
            cumulative += v/sum_sf
            roulette.append((k, cumulative))
        
        target_count = int(self.population * self.crossover)
        selected = set()
        while len(selected) < target_count:
            r = random.random()
            j = 0
            while r > roulette[j][1]:
                j += 1
            selected.add(roulette[j][0])
        return [g for g in genomes if g.name() in selected]

    def reproduce(self, fitness, genomes):
        """
        Performs single-point binary crossover.
        """
        new_genomes = set(genomes)
        while len(new_genomes) < self.population:
            new_genomes.update(Genome.crossover(*random.sample(genomes, 2)))
        new_genomes = list(new_genomes)[:self.population]
        return new_genomes
            
    def mutate(self, fitness, genomes):
        """
        Performs single bit binary mutation.
        """
        for g in genomes:
            g.mutate(prob=self.mutation)
        return genomes

    def generation(self, genomes):
        fitness = self.fitness(genomes)
        genomes = self.select(fitness, genomes)
        genomes = self.reproduce(fitness, genomes)
        genomes = self.mutate(fitness, genomes)
        return genomes
        
CHECK = lambda genomes: "%d genomes, %d unique, hash=%d" % (len(genomes), len(set(genomes)), hash(tuple(genomes)))

if __name__ == '__main__':                
        
    parser = argparse.ArgumentParser()
    parser.add_argument("--population", type=int, default=80)
    parser.add_argument("--generations", type=int, default=100)
    parser.add_argument("--mutation", type=float, default=0.01)
    parser.add_argument("--crossover", type=float, default=0.50)
    parser.add_argument("--players", type=int, default=4)
    parser.add_argument("--games", type=int, default=10)
    parser.add_argument("--workers", type=int, default=multiprocessing.cpu_count())

    args = parser.parse_args()

    p = Population(**args.__dict__)
    p.run()


