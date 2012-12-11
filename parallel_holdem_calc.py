import time
import holdem_functions
import holdem_argparser
from multiprocessing import Array, Pool, cpu_count


# Multiprocessing state variables
num_processes = cpu_count()
queues = []
winner_list = None
result_histograms = None


# Separated function for each thread to execute while running
def simulation(num_players, hole_cards, proc_id):
    global queues
    # Create results data structures which tracks results of comparisons
    # 1) result_list: list of the best possible poker hand for each pair of
    #    hole cards for a given board
    # 2) my_queue: task queue designated for current proc_id
    my_queue, result_list = queues[proc_id], []
    for player in xrange(num_players):
        result_list.append([])
    for board in my_queue:
        # Find the best possible poker hand given the created board and the
        # hole cards and save them in the results data structures
        (suit_histogram,
            histogram, max_suit) = holdem_functions.preprocess_board(board)
        for index, hole_card in enumerate(hole_cards):
            result_list[index] = holdem_functions.detect_hand(hole_card, board,
                                         suit_histogram, histogram, max_suit)
        # Find the winner of the hand and tabulate results
        winner_index = holdem_functions.compare_hands(result_list)
        winner_list[proc_id * (num_players + 1) + winner_index] += 1
        # Increment what hand each player made
        for index, result in enumerate(result_list):
            result_histograms[10 * (proc_id * num_players + index)
                                                          + result[0]] += 1


def main():
    # Data structures:
    # 1) result_histograms: a list for each player that shows the number of
    #    times each type of poker hand (e.g. flush, straight) was gotten
    # 2) winner_list: number of times each player wins the given round
    global winner_list, result_histograms, deck, queues
    # Parse command line arguments into hole cards and create deck
    (hole_cards, num_iterations,
                    exact, given_board, deck) = holdem_argparser.parse_args()
    num_players = len(hole_cards)
    # Create data structures to manage multiple processes
    winner_list = Array('i', num_processes * (num_players + 1))
    result_histograms = Array('i', num_processes * num_players * 10)
    # Choose whether we're running a Monte Carlo or exhaustive simulation
    board_length = 0 if given_board == None else len(given_board)
    # When a board is given, exact calculation is much faster than Monte Carlo
    # simulation, so default to exact if a board is given
    if exact or given_board is not None:
        generate_boards = holdem_functions.generate_exhaustive_boards
    else:
        generate_boards = holdem_functions.generate_random_boards
    # Generate all boards and take turns populating each queue with boards.
    proc_id = 0
    for process in xrange(num_processes):
        queues.append([])
    # TODO: Find a way to make this less memory intensive
    for remaining_board in generate_boards(deck, num_iterations, board_length):
        # Generate a new board
        if given_board:
            board = given_board[:]
            board.extend(remaining_board)
        else:
            board = remaining_board
        queues[proc_id].append(board)
        proc_id = (proc_id + 1) % num_processes
    # Create Process pool and create num_processes processes/task queues
    pool = Pool(processes=num_processes)
    for process in xrange(num_processes):
        pool.apply_async(simulation, args=(num_players, hole_cards, process))
    pool.close()
    pool.join()
    # Tallying and printing results
    combined_winner_list, combined_histograms = [0] * (num_players + 1), []
    for player in xrange(num_players):
        combined_histograms.append([0] * 10)
    # Go through each parallel data structure and aggregate results
    for index, element in enumerate(winner_list):
        combined_winner_list[index % (num_players + 1)] += element
    for index, element in enumerate(result_histograms):
        combined_histograms[(index / 10) % num_players][index % 10] += element
    # Print results
    holdem_functions.print_results(hole_cards, combined_winner_list,
                                                        combined_histograms)

if __name__ == '__main__':
    start = time.time()
    main()
    print "\nTime elapsed(seconds): ", time.time() - start
