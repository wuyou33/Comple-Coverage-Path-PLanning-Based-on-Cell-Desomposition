import cv2
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import sys
from helpers.graph import *
from helpers.geometry import *
from helpers.sweep import *
from helpers.util_mp import *
from helpers.util import *
import matplotlib.pyplot as plt
from tsp_solver.greedy import solve_tsp
import csv
import scipy.io as sio
import os


def generate_final_path(img_file_name, output_file_name, width, step, safeWidth):
    # img is the input image, approxes are the generated polygon
    img, approxes = generate_polygon_countour(img_file_name)
    for approx in approxes:
        img = cv2.drawContours(img, [approx], 0, (0, 255, 0), 3)

    # generate the boundary by getting the min/max value of all polygon
    polygons = [np.squeeze(x) for x in approxes]

    y_limit_lower = min([pt[1] for pt in polygons[0]])
    y_limit_upper = max([pt[1] for pt in polygons[0]])

    x_limit_lower = min([pt[0] for pt in polygons[0]])
    x_limit_upper = max([pt[0] for pt in polygons[0]])

    # boundary_basic certex order
    boundary_basic = [[x_limit_lower, y_limit_lower], [x_limit_upper, y_limit_lower], [x_limit_upper, y_limit_upper],
                      [x_limit_lower, y_limit_upper]]

    # Among all the polygon cv2 generated, [1:] are the inner obstacles
    obstacles_basic = polygons[1:]

    t = time.time()
    print('extract_vertex_mp')
    # boundary, sorted_vertices, obstacles = extract_vertex(boundary_basic, obstacles_basic)
    boundary, sorted_vertices, obstacles = extract_vertex_mp(boundary_basic, obstacles_basic)
    print("time:", time.time() - t)

    # generate vertical line
    t = time.time()
    print('get_vertical_line_mp')
    # open_line_segments = get_vertical_line(sorted_vertices, obstacles, y_limit_lower, y_limit_upper)
    open_line_segments = get_vertical_line_mp(sorted_vertices, obstacles, y_limit_lower, y_limit_upper)
    print("time:", time.time() - t)

    # Find Polygon cells naiively. Will improve next.
    # open_line_segments and sorted_vertices has the same order of points, based on the x_value
    t = time.time()
    print('generate_naive_polygon_mp')
    # quad_cells, left_tri_cells, right_tri_cells = generate_naive_polygon(open_line_segments, sorted_vertices, obstacles)
    quad_cells, left_tri_cells, right_tri_cells = generate_naive_polygon_mp(open_line_segments, sorted_vertices, obstacles)
    print("time:", time.time() - t)

    t = time.time()
    print('refine_quad_cells_mp')
    # refine_quad_cells(quad_cells)
    refine_quad_cells_mp(quad_cells)
    print("time:", time.time() - t)

    # Add boundary cell
    if (boundary[0].x != sorted_vertices[0].x):
        quad_cells.append(
            [boundary[0], point(sorted_vertices[0].x, y_limit_lower), point(sorted_vertices[0].x, y_limit_upper),
             boundary[3]]);
    if (boundary[1].x != sorted_vertices[len(sorted_vertices) - 1].x):
        quad_cells.append([point(sorted_vertices[len(sorted_vertices) - 1].x, y_limit_lower), boundary[1], boundary[2],
                           point(sorted_vertices[len(sorted_vertices) - 1].x, y_limit_upper)]);

    # combine all the cells
    all_cell = quad_cells + left_tri_cells + right_tri_cells
    # sort the cell based on teh x-value of the first point
    ################-----   IMPORTANT  -----##################
    all_cell.sort(key=lambda pnt: pnt[0].x)

    # genenrate node set, inside path without step
    t = time.time()
    print('generate_node_set_mp')
    # nodes = generate_node_set(all_cell, width, step, safeWidth=20)
    nodes = generate_node_set_mp(all_cell, width, step, safeWidth=20)
    print("time:", time.time() - t)

    # get the adjacency matrix
    adjacency_matrix = get_adjacency_matrix(nodes)

    # Dijkstra’s shortest path algorithm to get the shortest distance from the root to the target given adjacency matrix
    # use each node as root node iteratively to generate the distance matrix

    # generate a fully connected graph
    num_node = len(nodes)
    g = Graph(num_node)
    g.graph = adjacency_matrix
    g.generate_distance_st_matrix()

    distance_matrix = np.array(g.distance_matrix)

    # in order to use the solve_tsp command, we need to convert the distance matrix to a left_triangular_matrix
    left_tri_matrix = []
    for i in range(0, num_node):
        temp = list(np.split(distance_matrix[i], [i])[0])
        left_tri_matrix.append(temp)

    # use the tsp package to get the shortest path to visit all the nodes
    shortest_path_node = solve_tsp(left_tri_matrix, endpoints=(0, num_node - 1))
    # go back to the origin node 0
    shortest_path_node.append(shortest_path_node[0])

    # generate the path to travel through all node in shortest_path_node
    t = time.time()
    print('generate_path_mp')
    # new_path_node = generate_path(shortest_path_node, g.st_path_matrix, nodes, step)
    new_path_node = generate_path_mp(shortest_path_node, g.st_path_matrix, nodes, step)
    print("time:", time.time() - t)

    # final_path, include the inside path of each polygon
    final_path = []
    plt.figure(figsize=(20, 10))
    for i, node in enumerate(shortest_path_node):
        # go back to the origin node 0
        if (i < num_node):
            final_path = final_path + nodes[node].inside_path + new_path_node[i]

    draw_node(nodes, boundary, obstacles, fill=None)
    x = [pnt.x for pnt in final_path]
    y = [pnt.y for pnt in final_path]
    #     print("x-y")
    #     print(x)
    #     print(y)
    plt.plot(x, y)
    for pnt in final_path:
        plt.plot(pnt.x, pnt.y, marker='o')
    plt.show()


if __name__ == "__main__":
    print("Parent PID", os.getpid())
    generate_final_path("new_paint.png", "output.csv", 20, None, 20)
    print("Done!!!!!")
