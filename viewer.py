"""
Created By:    Cristian Scutaru
Creation Date: Aug 2023
Company:       XtractPro Software
"""

import sys, json, argparse, webbrowser, urllib.parse
import pandas as pd

def showUsage(msg=''):
    if len(msg) > 0: print(msg)
    print("Usage: python viewer.py options\n"
        "--f filename        - [required] CSV file name (with no file extension)\n"
        "--from column-name  - [required] name of the source child relationship column (used as identifier)\n"
        "--to column-name    - [required] name of the target parent relationship column (used as foreign key)\n"
        "--rev               - [optional] when true, the arrow will be directed from parent to child\n"
        "--d column-name     - [optional] name of a display column (or the 'from' column name will be used by default)\n"
        "--g column-name     - [optional] name of a column to group objects by\n"
        "--all               - [optional] expand all objects and show all related properties from the CSV file\n")
    sys.exit(2)

def processArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument('--f', dest='filename')
    parser.add_argument('--from', dest='fromCol')
    parser.add_argument('--to', dest='toCol')
    parser.add_argument('--rev', dest='rev', action=argparse.BooleanOptionalAction)
    parser.add_argument('--d', dest='displayCol')
    parser.add_argument('--g', dest='groupCol')
    parser.add_argument('--all', dest='all', action=argparse.BooleanOptionalAction)
    args = parser.parse_args()

    if (args.filename == None
        or args.fromCol == None
        or args.toCol == None):
        showUsage("You miss at least one required argument!")

    return args

def makeGraph(df, cols, fromCol, toCol, displayCol, groupCol, rev, all, filename):
    s = ""; t = ""

    # add groups (as subgraph clusters)
    if groupCol is not None:
        df = df.sort_values(by=[groupCol])
        t = "\t"

    # add nodes
    g = None; gps = 1;
    for _, row in df.iterrows():
        # read group and create subgroup cluster for next nodes
        # see https://stackoverflow.com/questions/2012036/graphviz-how-to-connect-subgraphs
        if groupCol is not None:
            grp = str(row[groupCol])
            if g is None or grp != g:
                if g is not None: s += '\n\t}'
                s += (f'\n\tsubgraph cluster{gps} {{\n'
                    + f'\t\tlabel="{grp}"')
                gps += 1; g = grp

        # add node (with label)
        label = str(row[fromCol]) if displayCol is None else str(row[displayCol])
        display = f' [label="{label}"]'
        if all:
            # get and show all row properties in the "exploded" node
            vals = ''
            for col in cols:
                if col != displayCol:
                    val = '&nbsp;' if pd.isnull(row[col]) else str(row[col])
                    vals += (f'\t\t<tr><td align="left"><font color="#000000">{col}&nbsp;</font></td>\n'
                        + f'\t\t<td align="left"><font color="#000000">{val}</font></td></tr>\n')

            display = (f' [ label=<<table style="rounded" border="0" cellborder="0" cellspacing="0" cellpadding="1">\n'
                + f'\t\t<tr><td align="center" colspan="2"><font color="#000000"><b>{label}</b></font></td></tr>\n'
                + f'{vals}\t\t</table>> ]')
        s += f'\n\t{t}n{str(row[fromCol])}{display};'
    if groupCol is not None and g is not None: s += '\n\t}'

    # add links
    for i, row in df.iterrows():
        if not pd.isna(row[toCol]):
            if rev: s += f'\n\tn{str(row[toCol])} -> n{str(row[fromCol])};'
            else: s += f'\n\tn{str(row[fromCol])} -> n{str(row[toCol])};'

    # add digraph around
    s = (f'digraph d {{\n'
        + f'\tgraph [rankdir="LR"; compound="True" color="Gray"];\n'
        + f'\tnode [shape="Mrecord" style="filled" color="SkyBlue"]'
        + f'{s}\n}}')
    with open(f"{filename}.dot", "w") as file:
        file.write(s)

    # url-encode as query string for remote Graphviz Visual Editor
    s = urllib.parse.quote(s)
    s = f'http://magjac.com/graphviz-visual-editor/?dot={s}'
    webbrowser.open(s)

def makeTree(df, fromCol, toCol, displayCol, filename):
    nodes = {}; head = None;

    # add nodes (to a local map)
    for _, row in df.iterrows():
        nFrom = str(row[fromCol])
        name = nFrom if displayCol is None else str(row[displayCol])
        nodes[nFrom] = { "name": name }
        if pd.isna(row[toCol]): head = nodes[nFrom]

    # add children to nodes
    for _, row in df.iterrows():
        nFrom = nodes[str(row[fromCol])]
        if not pd.isna(row[toCol]):
            nTo = nodes[str(row[toCol])]
            if "children" not in nTo: nTo["children"] = []
            nTo["children"].append(nFrom)

    # create HTML file from template customized with our JSON dump
    with open(f"data/template.html", "r") as file:
        s = file.read()

    s = s.replace('"{{data}}"', json.dumps(head, indent=4))
    with open(f"{filename}.html", "w") as file:
        file.write(s)
    webbrowser.open(s)
   
def main():
    args = processArgs()

    df = pd.read_csv(f"{args.filename}.csv").convert_dtypes()
    cols = list(map(str.upper, df.columns.values.tolist()))
    df = df.reset_index()  # make sure indexes pair with number of rows

    # validate column names
    fromCol = args.fromCol.upper()
    if fromCol not in cols: showUsage("'from' column not found!")
    
    toCol = args.toCol.upper()
    if toCol not in cols: showUsage("'to' column not found!")
    
    displayCol = None
    if args.displayCol is not None:
        displayCol = args.displayCol.upper()
        if displayCol not in cols: showUsage("'display' column not found!")
    
    groupCol = None
    if args.groupCol is not None:
        groupCol = args.groupCol.upper()
        if groupCol not in cols: showUsage("'group' column not found!")

    # generates and open GraphViz DOT graph, and D3 collapsible tree
    makeGraph(df, cols, fromCol, toCol, displayCol, groupCol, args.rev, args.all, args.filename)
    makeTree(df, fromCol, toCol, displayCol, args.filename)

if __name__ == '__main__':
  main()