from __future__ import annotations
import re
from typing import Callable
from copy import deepcopy
from random import shuffle


def print_args(*args, **kwargs) -> None:
    print(args, kwargs)
    raise ValueError("print_args will always raise after use")


class Profile:
    def __init__(self, filename) -> None:
        """
        Loads a TOI file from PrefLib.
        Returns a list of ballots, each as:
            (votes, [ranked alternatives in ballot])
        """
        ballots = []
        self.alternatives = set()
        with open(filename, "r") as f:
            for line in f:
                if line.startswith("#") or ":" not in line:
                    continue
                votes_part, ballot_part = line.split(":")
                votes = int(votes_part.strip())
                ballot_part = ballot_part.strip()

                if ballot_part == "":
                    ranks = []
                else:
                    # remove any non-digit characters and split by comma (ChatGPT)
                    ranks = [
                        int(re.sub(r"\D", "", x))
                        for x in ballot_part.split(",")
                        if re.sub(r"\D", "", x)
                    ]

                self.alternatives |= set(ranks)
                ballots.append([votes, ranks])

        self.ballots: list = ballots

    def __str__(self) -> str:
        return "\n".join(str(i) for i in self.ballots)

    def __eq__(self, other: Profile) -> bool:
        return self.ballots == other.ballots

    def __len__(self) -> int:
        return sum(i[0] for i in self.ballots)

    def __next__(self):
        for i in self.ballots:
            print(i, type(i))
            yield i

    def __iter__(self):
        return self

    def plurality_scores(self, active):
        """
        Compute plurality score of each candidate in 'active':
        Count how many ballots rank the candidate first *among active candidates*.
        """
        score = {c: 0 for c in active}

        for votes, ranking in self.ballots:
            # find first-ranked active candidate
            for cand in ranking:
                if cand in active:
                    score[cand] += votes
                    break

        return score

    def add_ballot(self, n_voters: int, ballot: list[int]) -> None:
        # replace with something more efficient
        for i, vote in enumerate(self.ballots):
            if vote[1] == ballot:
                self.ballots[i][0] += n_voters
                break
        else:
            self.ballots.append([n_voters, ballot])

    def apply_coalition(self, coalition: Profile, shared_vote: list[int]) -> None:
        if not len(coalition):
            return
        for coalition_ballot in coalition.ballots:
            for ballot in self.ballots:
                if ballot[1] == coalition_ballot[1]:
                    ballot[0] -= coalition_ballot[0]

        self.ballots = [i for i in self.ballots if i[0]]
        self.add_ballot(len(coalition), shared_vote)

    def stv_rule(self, num_candidates):
        """
        Implements STV. Returns a list of winners (those eliminated last).
        """

        # start with full candidate set
        active = set(range(1, num_candidates + 1))

        elimination_order = []  # each round: the set of eliminated candidates

        while active:
            scores = self.plurality_scores(active)

            # minimum plurality score among remaining candidates
            min_score = min(scores.values())

            # all candidates with the minimum score are eliminated
            to_eliminate = {c for c, s in scores.items() if s == min_score}

            elimination_order.append(to_eliminate)

            # remove them from active set
            active -= to_eliminate

        # the winners = last elimination step
        winners = elimination_order[-1]
        return winners, elimination_order

    def force_stv_winner(self, alternative: int) -> list[int]:
        active = set(range(1, num_candidates + 1))

        elimination_order = []  # each round: the set of eliminated candidates
        savior_sizes = []

        while len(active) > 1:
            scores = self.plurality_scores(active)

            score_list = sorted(list(scores.values()))

            # print(alternative, scores, score_list)
            # minimum plurality score among remaining candidates
            min_score = min(score_list)

            # all candidates with the minimum score are eliminated
            to_eliminate = {c for c, s in scores.items() if s == min_score}
            # print(to_eliminate)
            if alternative in to_eliminate:
                score_list.pop(0)
                new_min_score = min(score_list)
                to_eliminate = {c for c, s in scores.items() if s == new_min_score}
                to_eliminate -= {alternative}

                # print(score_list)
                savior_sizes.append(new_min_score - min_score + 1)
            else:
                savior_sizes.append(0)

            elimination_order.append(to_eliminate)

            # remove them from active set
            active -= to_eliminate

        # the winners = last elimination step
        winners = elimination_order[-1]
        return savior_sizes

    def filter_ballots(self, condition: Callable[[int, list[int]], int]) -> None:
        self.ballots = [i for i in self.ballots if condition(*i)]

    def order_ballots(self, key: Callable[[int, list[int]], int | float]) -> None:
        self.ballots.sort(key=key)

    def remove_alternative(self, alternative: int) -> None:
        for ballot in self.ballots:
            if alternative in ballot[0]:
                ballot[0].remove(alternative)

    def take_n(self, n: int) -> None:
        """Keeps the first n ballots, and discards the rest"""
        new_ballots = []
        for number, rank in self.ballots:
            if not n:
                break
            elif number >= n:
                new_ballots.append([n, rank])
                break
            else:
                new_ballots.append([number, rank])
                n -= number

        self.ballots = new_ballots


def minimum_adjustment(profile: Profile):
    winner = profile.stv_rule(11)[0]
    print(winner)
    print(
        {
            a: profile.force_stv_winner(a)
            for a in profile.alternatives - winner - {10, 11}
        }
    )
    adjustments = {
        a: max(profile.force_stv_winner(a))
        for a in profile.alternatives - winner - {10, 11}
    }
    print(adjustments)
    return sorted(adjustments.items(), key=lambda x: x[1])


def remove_alternative_voters(profile: Profile, alternative: int):
    def alternative_ranked_highest(_, ballot: list[int]):
        return ballot[0] == alternative

    profile.filter_ballots(alternative_ranked_highest)


def one_alternative_first(
    rank: list[set], alternative_one: int, alternative_two: int
) -> bool:
    """returns true if alternative one is ranked higher or equal to alternative two"""
    for i in rank:
        if alternative_one == i:
            return True
        if alternative_two == i:
            return False
    return False


def lower_ranked_ness(rank: list[set], alternative: int) -> int:
    badness = 0
    turn = False
    for a in rank:
        if alternative == a:
            turn = True
        badness += 1 if turn else -1

    return badness


def new_algorithm(profile: Profile) -> tuple[int, Profile]:
    winner = next(iter(profile.stv_rule(11)[0]))
    best_coalition = None
    print("New algorithm; old winner: ", winner, profile.stv_rule(11)[0])
    minimum = 1000
    for a, min_adjustment in minimum_adjustment(profile):
        min_adjustment += 100
        min_adjustment = min(min_adjustment, minimum)
        new_profile_base = deepcopy(profile)
        new_profile_base.filter_ballots(
            lambda n, x: not one_alternative_first(x, winner, a)
        )
        new_profile_base.order_ballots(lambda x: not lower_ranked_ness(x[1], a))
        print("New possible coalition profile size:", len(new_profile_base))
        adjustment_works = True
        while adjustment_works and min_adjustment:
            new_profile = deepcopy(new_profile_base)
            new_profile.take_n(min_adjustment)

            new_testing_profile = deepcopy(profile)
            new_testing_profile.apply_coalition(new_profile, [a])
            result = new_testing_profile.stv_rule(11)[0]
            new_winner = next(iter(result))
            print(
                "New algorithm; new winner",
                new_winner,
                ", ",
                result,
                ", for alternative:",
                a,
                ", with coalition size:",
                min_adjustment,
            )
            adjustment_works = new_winner != winner
            print(adjustment_works, min_adjustment, minimum)
            if adjustment_works and min_adjustment < minimum:
                minimum = min_adjustment
                best_coalition = deepcopy(new_profile)
            min_adjustment -= 1
            if not adjustment_works and minimum > min_adjustment + 2:
                min_adjustment += 2
                adjustment_works = True

    return minimum, best_coalition


if __name__ == "__main__":
    ballots = Profile("dataset.toi.txt")
    num_candidates = 11

    winners, elimination_order = ballots.stv_rule(num_candidates)

    print("STV winners:", winners)
    print("Elimination order (from first eliminated to last):")
    for step, eliminated in enumerate(elimination_order, 1):
        print(f"Round {step}: eliminated {eliminated}")

    print("minimum adjustment:", minimum_adjustment(ballots))
    # ballots.take_n(100)
    # print(ballots)
    # new_ballots = deepcopy(ballots)
    # coalition = deepcopy(ballots)
    # print(ballots == new_ballots)
    # coalition.take_n(50)
    # print(coalition)
    # print("end_coalition")
    # new_ballots.apply_coalition(coalition, [0])
    # print(new_ballots)
    # print(ballots == new_ballots)
    # print(ballots)
    shuffle(ballots.ballots)
    # print(ballots)
    # ballots.take_n(100)
    print(new_algorithm(ballots))
