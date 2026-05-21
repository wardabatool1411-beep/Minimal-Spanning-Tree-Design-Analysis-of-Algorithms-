import asyncio
import math
from pyscript import document, window
from pyodide.ffi import create_proxy

class GraphApp:
    def __init__(self):
        self.nodes = []
        self.edges = []
        self.mode = 'node'
        self.is_running = False
        self.is_dragging = False
        self.selected_node = None
        self.mouse_pos = {'x': 0, 'y': 0}
        
        self.canvas = document.querySelector("#graphCanvas")
        self.ctx = self.canvas.getContext("2d")
        self.resize()

    def resize(self):
        self.canvas.width = self.canvas.offsetWidth
        self.canvas.height = self.canvas.offsetHeight

    def find_node(self, x, y):
        for n in self.nodes:
            if math.hypot(n['x'] - x, n['y'] - y) < 22:
                return n
        return None

    def update_matrix(self):
        container = document.querySelector("#matrixContainer")
        if not self.nodes:
            container.innerText = "No nodes yet"
            return
        
        size = len(self.nodes)
        matrix = [[0] * size for _ in range(size)]
        for e in self.edges:
            u, v = e['u']['id'], e['v']['id']
            matrix[u][v] = matrix[v][u] = e['weight']
        
        header = "    " + " ".join([str(i).rjust(2) for i in range(size)]) + "\n"
        rows = ""
        for i, row in enumerate(matrix):
            rows += f"{str(i).ljust(2)} [{','.join([str(val).rjust(2, '0') for val in row])}]\n"
        container.innerText = header + rows

    def render(self):
        self.ctx.clearRect(0, 0, self.canvas.width, self.canvas.height)
        
    
        if self.is_dragging and self.selected_node:
            self.ctx.beginPath()
            self.ctx.setLineDash([5, 5])
            self.ctx.moveTo(self.selected_node['x'], self.selected_node['y'])
            self.ctx.lineTo(self.mouse_pos['x'], self.mouse_pos['y'])
            self.ctx.strokeStyle = "#94a3b8"
            self.ctx.stroke()
            self.ctx.setLineDash([])

    
        for e in self.edges:
            self.ctx.beginPath()
            self.ctx.moveTo(e['u']['x'], e['u']['y'])
            self.ctx.lineTo(e['v']['x'], e['v']['y'])
            self.ctx.lineWidth = 6 if e.get('inMST') else 2
            
            if e.get('inMST'): color = "#2ecc71"
            elif e.get('visiting'): color = "#f1c40f"
            else: color = "#cbd5e1"
            
            self.ctx.strokeStyle = color
            self.ctx.stroke()
            # Weight text
            self.ctx.fillStyle = "#1e293b"
            self.ctx.font = "bold 12px Inter"
            self.ctx.fillText(str(e['weight']), (e['u']['x']+e['v']['x'])/2, (e['u']['y']+e['v']['y'])/2 - 5)

        
        for n in self.nodes:
            self.ctx.beginPath()
            self.ctx.arc(n['x'], n['y'], 18, 0, math.pi*2)
            self.ctx.fillStyle = "#3498db"
            self.ctx.fill()
            self.ctx.strokeStyle = "#2980b9"
            self.ctx.stroke()
            self.ctx.fillStyle = "white"
            self.ctx.textAlign = "center"
            self.ctx.fillText(str(n['id']), n['x'], n['y'] + 5)

    async def run_prims(self, event):
        if len(self.nodes) < 2 or self.is_running: return
        self.is_running = True
        for e in self.edges: e['inMST'] = False
        
        document.querySelector("#iterBody").innerHTML = ""
        document.querySelector("#finalCost").innerText = ""
        visited = {0}
        total_w = 0

        while len(visited) < len(self.nodes):
            min_edge = None
            min_w = float('inf')
            speed = (2100 - int(document.querySelector("#speedSlider").value)) / 1000
            
            document.querySelector("#statusLabel").innerText = "Probing connected edges..."
            
            for e in self.edges:
                u_in, v_in = e['u']['id'] in visited, e['v']['id'] in visited
                if (u_in and not v_in) or (not u_in and v_in):
                    e['visiting'] = True
                    if e['weight'] < min_w:
                        min_w, min_edge = e['weight'], e
            
            self.render()
            await asyncio.sleep(speed)

            if min_edge:
                min_edge['inMST'] = True
                new_n = min_edge['v']['id'] if min_edge['u']['id'] in visited else min_edge['u']['id']
                visited.add(new_n)
                total_w += min_edge['weight']
                
                row = document.createElement("tr")
                row.innerHTML = f"<td>{min_edge['u']['id']}↔{min_edge['v']['id']}</td><td>{min_edge['weight']}</td>"
                document.querySelector("#iterBody").appendChild(row)
                document.querySelector("#finalCost").innerText = f"MST Total: {total_w}"
            else:
                document.querySelector("#statusLabel").innerText = "Graph Disconnected!"
                break
            
            for e in self.edges: e['visiting'] = False
            self.render()
            await asyncio.sleep(0.1)

        document.querySelector("#statusLabel").innerText = "Prim's Finished!"
        self.is_running = False

app = GraphApp()

def mousedown(e):
    if app.is_running: return
    rect = app.canvas.getBoundingClientRect()
    x, y = e.clientX - rect.left, e.clientY - rect.top
    if app.mode == 'node':
        if not app.find_node(x, y):
            app.nodes.append({'x': x, 'y': y, 'id': len(app.nodes)})
            app.update_matrix()
    else:
        node = app.find_node(x, y)
        if node:
            app.selected_node = node
            app.is_dragging = True
            app.mouse_pos = {'x': x, 'y': y}
    app.render()

def mousemove(e):
    if app.is_dragging:
        rect = app.canvas.getBoundingClientRect()
        app.mouse_pos = {'x': e.clientX - rect.left, 'y': e.clientY - rect.top}
        app.render()

def mouseup(e):
    if app.mode == 'edge' and app.is_dragging:
        rect = app.canvas.getBoundingClientRect()
        target = app.find_node(e.clientX - rect.left, e.clientY - rect.top)
        if target and target != app.selected_node:
            exists = any((ed['u']==app.selected_node and ed['v']==target) or (ed['v']==app.selected_node and ed['u']==target) for ed in app.edges)
            if not exists:
                w = int(math.hypot(app.selected_node['x']-target['x'], app.selected_node['y']-target['y'])/10)
                app.edges.append({'u': app.selected_node, 'v': target, 'weight': w})
                app.update_matrix()
    app.is_dragging = False
    app.render()

def set_node_mode(e):
    app.mode = 'node'
    document.querySelector("#addNodeBtn").className = "active"
    document.querySelector("#addEdgeBtn").className = ""
def set_edge_mode(e):
    app.mode = 'edge'
    document.querySelector("#addEdgeBtn").className = "active"
    document.querySelector("#addNodeBtn").className = ""

document.querySelector("#addNodeBtn").onclick = set_node_mode
document.querySelector("#addEdgeBtn").onclick = set_edge_mode
document.querySelector("#runBtn").onclick = create_proxy(app.run_prims)
document.querySelector("#clearBtn").onclick = lambda e: window.location.reload()
app.canvas.onmousedown = create_proxy(mousedown)
app.canvas.onmousemove = create_proxy(mousemove)
app.canvas.onmouseup = create_proxy(mouseup)

app.resize()
app.render()