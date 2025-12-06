import re

def load_toi(filename):
    """
    Loads a TOI file from PrefLib.
    Returns a list of ballots, each as:
        (votes, [ranked alternatives in ballot])
    """
    ballots = []
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
                ranks = [int(re.sub(r"\D", "", x)) for x in ballot_part.split(",") if re.sub(r"\D", "", x)]
            
            ballots.append((votes, ranks))
    return ballots



def plurality_scores(ballots, active):
    """
    Compute plurality score of each candidate in 'active':
    Count how many ballots rank the candidate first *among active candidates*.
    """
    score = {c: 0 for c in active}

    for votes, ranking in ballots:
        # find first-ranked active candidate
        for cand in ranking:
            if cand in active:
                score[cand] += votes
                break

    return score


def stv_rule(ballots, num_candidates):
    """
    Implements STV. Returns a list of winners (those eliminated last).
    """

    # start with full candidate set
    active = set(range(1, num_candidates + 1))

    elimination_order = []  # each round: the set of eliminated candidates

    while active:
        scores = plurality_scores(ballots, active)

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


if __name__ == "__main__":
    ballots = load_toi("dataset.toi.txt")
    num_candidates = 11

    winners, elimination_order = stv_rule(ballots, num_candidates)

    print("STV winners:", winners)
    print("Elimination order (from first eliminated to last):")
    for step, eliminated in enumerate(elimination_order, 1):
        print(f"Round {step}: eliminated {eliminated}")
