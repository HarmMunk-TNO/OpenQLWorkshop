import numpy as np
p0 = np.random.random()
target_distr = {0: p0, 1: 1-p0}
print(f"{p0} .. {1-p0}")

from openql import openql as ql
import math

#For now, we'll use only one qbit
nqubits = 1

# We'll do 1024 shots in a simulation
n_shots = 1024

# Some housekeeping:
# - file extension for cQASM files:
cqasm_ext = ".qasm"
# - the directory where the cQASM file and the QXelarator output results are stored:
output_dir = "output/"
# - the prefix for all files resulting from this experiment:
prefix = "VQE"
# - name of the file containing the cQASM representation of the quantum circuit
cqasm_qc_file = output_dir + prefix + cqasm_ext
# - name of the file containing the simulation results
sim_result_file = output_dir + prefix + "_simulation_result.json"

def get_var_form(params):
    # Initialise OpenQL:
    # - make sure the compiler is (re)initialised before we construct a new quantum circuit
    ql.initialize()
    # - set the directory where the cQASM file are stored
    ql.set_option('output_dir', output_dir)
    # - set the logging level to 'information'
    ql.set_option('log_level', 'LOG_INFO')

    # Define the platform. We'll use the default platform
    platform = ql.Platform('MyPlatform', 'none')
        
    # Define the program 'VQE'. The program will be run on 'platform', and it will use 1 qbit
    VQE = ql.Program(prefix, platform, nqubits)
    
    # The following four lines are 'magic' to make sure OpenQL produces cQASM 1.0
    # After QXelerator is upgraded to cQASM 1.2, these lines (should) become obsolete
    VQE.get_compiler().set_option('initialqasmwriter.cqasm_version', '1.0')
    VQE.get_compiler().set_option('initialqasmwriter.with_metadata', 'no')
    VQE.get_compiler().set_option('scheduledqasmwriter.cqasm_version', '1.0')
    VQE.get_compiler().set_option('scheduledqasmwriter.with_metadata', 'no')
    
    # An OpenQL program consists of kernels.
    # Here we have three kernels: preparation, universal 3 parameter quantum circuit, and a measurement
    prep = ql.Kernel('prep', platform, nqubits)
    u3_1 = ql.Kernel('u3_1', platform, nqubits)
    u3_2 = ql.Kernel('u3_2', platform, nqubits)
    meas = ql.Kernel('meas', platform, nqubits)
    
    q = 0  # The number of the qubit used in the following statements
    
    prep.prepz(q)         # Set the qbit in a zero state
    
    u3_1.rz(q, params[2])           # Rotate over  params[2] radians around the z-axis
    u3_1.rx(q, math.pi/2)           # Rotate over pi/2 radians around the x-axis
    u3_1.rz(q, params[0] + math.pi) # Rotate over angle params[0] + pi radians around the z-axis
    u3_1.rx(q, math.pi/2)           # Rotate over pi/2 radians around the x-axis
    u3_1.rz(q, params[1] + math.pi) # Rotate over params[1]  + pi radians around the z-axis
    
    u3_2.rz(q, params[0])
    u3_2.ry(q, params[1])
    u3_2.rz(q, params[2])
    
    meas.measure(q)       # Measure the qbit
    
    # Attach the kernels to the program VQE in the proper order
    VQE.add_kernel(prep)
    VQE.add_kernel(u3_1)
    VQE.add_kernel(meas)
    
    # Finally, compile the program VQE
    VQE.compile()
    
    # Done, return the program VQE
    return VQE

myProgram = get_var_form([0, 0, 0])

import os
print(os.listdir(output_dir))

with open(cqasm_qc_file) as file:
    print(file.read())

with open(output_dir + prefix + "_scheduled.qasm") as file:
    print(file.read())

import qxelarator

# Define a qxelarator
qx = qxelarator.QX()

# Set the file where the simulation output is stored
qx.set_json_output_path(sim_result_file)

# Load the cQASM file in the simulator
qx.set(cqasm_qc_file)

import json

# Simualte the circuit 1024 times. The result is stored in the 'sim_result_file' in JSON format
qx.execute(1024)

# Get the result
with open(sim_result_file) as file:
    res = json.loads(file.read())
print(res)

# Get the result, and convert from JSON into a Python dictionary
with open(sim_result_file) as file:
    res = json.loads(file.read())
print(res)

def result_to_distr(simulation_result):
    results = simulation_result['results']
    return  [results.get('0000000000', 0.0), results.get('0000000001', 0.0)]

cost_values=[]

def objective_function(params):
    # Create circuit
    qc = get_var_form(params)
    
    # Simulate circuit
#    qx = qxelarator.QX()
#    qx.set_json_output_path(sim_result_file) # output/VQE_simulation_result.json
    qx.set(cqasm_qc_file) # output/VQE.qasm
    qx.execute(n_shots)
    
    # Get the results
    with open(sim_result_file) as file:
        simulation_result = json.loads(file.read())
    output_distr = result_to_distr(simulation_result)
    cost = sum(abs(target_distr.get(i, 0) - output_distr[i])
              for i in range(2**nqubits))
    global cost_values
    cost_values += [cost]
    return cost

params = np.random.rand(3)
objective_function([0,0,0])

from scipy.optimize import minimize

params = np.random.rand(3)
params = [0.0, 0.0, 0.0]
cost_values=[]
result = minimize(fun=objective_function, x0=params, method="COBYLA", options={'maxiter': 500, 'tol': 0.0001})
print(result)

qc = get_var_form(result.x)
qx.execute(10000)
with open(sim_result_file) as file:
        simulation_result = json.loads(file.read())
output_distr = result_to_distr(simulation_result)

print(f"Parameters found: {result.x}")
print(f"Target distribution: {(target_distr)}")
print(f"Obtained distribution: {output_distr}")
print(f"Cost: {objective_function(result.x)}")

import matplotlib.pyplot as plt
plt.plot(cost_values)
plt.ylabel('cost')
plt.show()


