import numpy as np
from flask import Flask, render_template, request, jsonify
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit_aer import Aer
from qiskit.quantum_info import random_statevector, random_unitary
import json
import random

app = Flask(__name__)

# ================================================
# 🔐 Base QKD Protocol Class
# ================================================
class QKDProtocol:
    """Base class for Quantum Key Distribution (QKD) protocols"""

    def __init__(self, name, description):
        self.name = name
        self.description = description
    
    def generate_key(self, key_length, include_eavesdropping=False, custom_bits=None):
        """
        Abstract method to generate a quantum key.
        (Implemented by subclasses such as BB84, E91, etc.)
        """
        pass
    
    def calculate_security_metrics(self, alice_key, bob_key, eavesdropping=False):
        """
        Calculate the Quantum Bit Error Rate (QBER) and key agreement rate.
        Determines whether the communication is secure or compromised.
        """
        if not alice_key or not bob_key:
            return {
                'agreement_rate': 0.0,
                'qber': 1.0,
                'is_secure': False,
                'security_level': 'Low'
            }

        # Compare Alice’s and Bob’s bits to calculate QBER
        total = min(len(alice_key), len(bob_key))
        matches = sum(1 for i, j in zip(alice_key[:total], bob_key[:total]) if i == j)
        agreement_rate = matches / total
        qber = 1.0 - agreement_rate

        # Security evaluation thresholds
        is_secure = qber < 0.15
        security_level = 'High' if qber < 0.05 else 'Medium' if qber < 0.15 else 'Low'

        return {
            'agreement_rate': agreement_rate,
            'qber': qber,
            'is_secure': is_secure,
            'security_level': security_level
        }

    def build_circuit(self):
        """Return a representative QuantumCircuit for visualization."""
        raise NotImplementedError

    def get_circuit_text(self, key_length=4):
        """Return ASCII visualization of the quantum circuit."""
        qc = self.build_circuit(key_length)
        return str(qc.draw(output='text'))


# ================================================
# 🧩 BB84 Protocol (Photon polarization-based QKD)
# ================================================
class BB84Protocol(QKDProtocol):
    """BB84 Protocol Implementation"""

    def __init__(self):
        super().__init__("BB84", "First practical quantum key distribution protocol using photon polarization")
    
    def generate_key(self, key_length, include_eavesdropping=False, custom_bits=None):
        """
        Generates a shared secret key using the BB84 protocol.
        - Alice randomly chooses bits and bases.
        - Bob randomly chooses bases for measurement.
        - Only bits with matching bases are kept (sifted key).
        - Optionally simulates eavesdropping by Eve.
        - If custom_bits provided, uses those directly as Alice's key.
        """
        backend = Aer.get_backend('qasm_simulator')
        
        # If custom bits provided, use them directly as Alice's key
        if custom_bits:
            custom_bit_list = [int(bit) for bit in custom_bits]
            if len(custom_bit_list) < key_length:
                raise ValueError(f"Custom bits must be at least {key_length} bits long")
            
            # Use custom bits directly as Alice's key
            alice_key = custom_bit_list[:key_length]
            
            # Generate Bob's key through quantum simulation
            bob_key = []
            bit_index = 0
            
            while len(bob_key) < key_length:
                alice_basis = random.randint(0, 1)  # 0 = rectilinear, 1 = diagonal
                bob_basis = random.randint(0, 1)

                qc = QuantumCircuit(1, 1)
                
                # Use Alice's custom bit
                alice_bit = alice_key[bit_index]
                if alice_bit == 1:
                    qc.x(0)
                
                if alice_basis == 1:  # Diagonal basis (Hadamard)
                    qc.h(0)
                
                # --- Optional Eavesdropping Simulation ---
                if include_eavesdropping and random.random() < 0.3:
                    eve_basis = random.randint(0, 1)
                    if eve_basis == 1:
                        qc.h(0)
                    qc.measure(0, 0)
                    job = backend.run(qc, shots=1, memory=True)
                    result = job.result()
                    eve_result = int(result.get_memory()[0])
                    
                    # Eve resends her measured qubit to Bob
                    qc = QuantumCircuit(1, 1)
                    if eve_result == 1:
                        qc.x(0)
                    if eve_basis == 1:
                        qc.h(0)
                
                # --- Bob measures the incoming qubit ---
                if bob_basis == 1:
                    qc.h(0)
                qc.measure(0, 0)
                
                # Execute quantum simulation
                job = backend.run(qc, shots=1, memory=True)
                result = job.result()
                bob_result = int(result.get_memory()[0])
                
                # --- Basis reconciliation (keep only matching bases) ---
                if alice_basis == bob_basis:
                    bob_key.append(bob_result)
                    bit_index += 1
        else:
            # Original random generation logic
            alice_key = []
            bob_key = []
            
            # Continue until enough valid (matching-basis) bits are collected
            while len(alice_key) < key_length:
                # --- Step 1: Alice randomly prepares a qubit ---
                alice_bit = random.randint(0, 1)
                alice_basis = random.randint(0, 1)  # 0 = rectilinear, 1 = diagonal
                bob_basis = random.randint(0, 1)

                qc = QuantumCircuit(1, 1)
                
                if alice_bit == 1:
                    qc.x(0)
                
                if alice_basis == 1:  # Diagonal basis (Hadamard)
                    qc.h(0)
                
                # --- Step 2: Optional Eavesdropping Simulation ---
                if include_eavesdropping and random.random() < 0.3:
                    eve_basis = random.randint(0, 1)
                    if eve_basis == 1:
                        qc.h(0)
                    qc.measure(0, 0)
                    job = backend.run(qc, shots=1, memory=True)
                    result = job.result()
                    eve_result = int(result.get_memory()[0])
                    
                    # Eve resends her measured qubit to Bob
                    qc = QuantumCircuit(1, 1)
                    if eve_result == 1:
                        qc.x(0)
                    if eve_basis == 1:
                        qc.h(0)
                
                # --- Step 3: Bob measures the incoming qubit ---
                if bob_basis == 1:
                    qc.h(0)
                qc.measure(0, 0)
                
                # Execute quantum simulation
                job = backend.run(qc, shots=1, memory=True)
                result = job.result()
                bob_result = int(result.get_memory()[0])
                
                # --- Step 4: Basis reconciliation (keep only matching bases) ---
                if alice_basis == bob_basis:
                    alice_key.append(alice_bit)
                    bob_key.append(bob_result)
        
        # --- Return generated keys ---
        return {
            'alice_key': alice_key,
            'bob_key': bob_key,
            'protocol': self.name,
            'eavesdropping': include_eavesdropping
        }

    def build_circuit(self, key_length=4):
        """Representative BB84 circuit for visualization only."""
        num_qubits = key_length
        qc = QuantumCircuit(num_qubits, num_qubits)
        
        for i in range(num_qubits):
            if i % 2 == 0:
                qc.measure(i, i)
            else:
                qc.h(i)
                qc.measure(i, i)
        
        return qc


# ================================================
# 🔗 E91 Protocol (Entanglement-based QKD)
# ================================================
class E91Protocol(QKDProtocol):
    """E91 Protocol using entangled Bell states"""

    def __init__(self):
        super().__init__("E91", "Entanglement-based QKD protocol using Bell states")
    
    def generate_key(self, key_length, include_eavesdropping=False, custom_bits=None):
        """
        E91 QKD uses pairs of entangled qubits shared between Alice and Bob.
        They measure in different bases and use correlated results to generate a key.
        If custom_bits provided, uses those directly as Alice's key.
        """
        backend = Aer.get_backend('qasm_simulator')
        
        # If custom bits provided, use them directly as Alice's key
        if custom_bits:
            custom_bit_list = [int(bit) for bit in custom_bits]
            if len(custom_bit_list) < key_length:
                raise ValueError(f"Custom bits must be at least {key_length} bits long")
            
            # Use custom bits directly as Alice's key
            alice_key = custom_bit_list[:key_length]
            
            # Generate Bob's key through quantum simulation
            bob_key = []
            bit_index = 0
            
            while len(bob_key) < key_length:
                qc = QuantumCircuit(2, 2)
                # --- Step 1: Create entangled pair ---
                qc.h(0)
                qc.cx(0, 1)
                
                # --- Step 2: Random measurement bases for Alice & Bob ---
                alice_basis = random.randint(0, 2)
                bob_basis = random.randint(0, 2)
                
                if alice_basis == 1:
                    qc.h(0)
                elif alice_basis == 2:
                    qc.sdg(0); qc.h(0)
                
                if bob_basis == 1:
                    qc.h(1)
                elif bob_basis == 2:
                    qc.sdg(1); qc.h(1)
                
                # --- Step 3: Optional eavesdropping simulation ---
                if include_eavesdropping and random.random() < 0.25:
                    qc.measure_all()
                    job = backend.run(qc, shots=1, memory=True)
                    eve_results = job.result().get_memory()[0]
                    
                    # Eve recreates imperfect entanglement
                    qc = QuantumCircuit(2, 2)
                    if eve_results[1] == '1': qc.x(0)
                    if eve_results[0] == '1': qc.x(1)
                    qc.h(0); qc.cx(0, 1)
                    if random.random() < 0.1: qc.x(random.randint(0, 1))
                
                # --- Step 4: Measurement ---
                qc.measure(0, 0); qc.measure(1, 1)
                result = backend.run(qc, shots=1, memory=True).result()
                measurements = result.get_memory()[0]
                
                # --- Step 5: Use only matching bases ---
                if alice_basis == bob_basis:
                    bob_bit = int(measurements[0])
                    if alice_basis == 2:  # flip Y basis correlation
                        bob_bit = 1 - bob_bit
                    bob_key.append(bob_bit)
                    bit_index += 1
        else:
            # Original random generation logic
            alice_key, bob_key = [], []
            
            while len(alice_key) < key_length:
                qc = QuantumCircuit(2, 2)
                # --- Step 1: Create entangled pair ---
                qc.h(0)
                qc.cx(0, 1)
                
                # --- Step 2: Random measurement bases for Alice & Bob ---
                alice_basis = random.randint(0, 2)
                bob_basis = random.randint(0, 2)
                
                if alice_basis == 1:
                    qc.h(0)
                elif alice_basis == 2:
                    qc.sdg(0); qc.h(0)
                
                if bob_basis == 1:
                    qc.h(1)
                elif bob_basis == 2:
                    qc.sdg(1); qc.h(1)
                
                # --- Step 3: Optional eavesdropping simulation ---
                if include_eavesdropping and random.random() < 0.25:
                    qc.measure_all()
                    job = backend.run(qc, shots=1, memory=True)
                    eve_results = job.result().get_memory()[0]
                    
                    # Eve recreates imperfect entanglement
                    qc = QuantumCircuit(2, 2)
                    if eve_results[1] == '1': qc.x(0)
                    if eve_results[0] == '1': qc.x(1)
                    qc.h(0); qc.cx(0, 1)
                    if random.random() < 0.1: qc.x(random.randint(0, 1))
                
                # --- Step 4: Measurement ---
                qc.measure(0, 0); qc.measure(1, 1)
                result = backend.run(qc, shots=1, memory=True).result()
                measurements = result.get_memory()[0]
                
                # --- Step 5: Use only matching bases ---
                if alice_basis == bob_basis:
                    alice_bit = int(measurements[1])
                    bob_bit = int(measurements[0])
                    if alice_basis == 2:  # flip Y basis correlation
                        bob_bit = 1 - bob_bit
                    alice_key.append(alice_bit)
                    bob_key.append(bob_bit)
        
        return {'alice_key': alice_key, 'bob_key': bob_key, 'protocol': self.name, 'eavesdropping': include_eavesdropping}


# ================================================
# 🧬 BBM92 Protocol (Bell-state based QKD)
# ================================================
class BBM92Protocol(QKDProtocol):
    """BBM92 Protocol using Bell-state correlations"""

    def __init__(self):
        super().__init__("BBM92", "Bell state measurement based QKD protocol")
    
    def generate_key(self, key_length, include_eavesdropping=False, custom_bits=None):
        """
        Similar to E91 but focuses only on matching basis measurements of entangled photons.
        If custom_bits provided, uses those directly as Alice's key.
        """
        backend = Aer.get_backend('qasm_simulator')
        
        # If custom bits provided, use them directly as Alice's key
        if custom_bits:
            custom_bit_list = [int(bit) for bit in custom_bits]
            if len(custom_bit_list) < key_length:
                raise ValueError(f"Custom bits must be at least {key_length} bits long")
            
            # Use custom bits directly as Alice's key
            alice_key = custom_bit_list[:key_length]
            
            # Generate Bob's key through quantum simulation
            bob_key = []
            bit_index = 0
            
            while len(bob_key) < key_length:
                qc = QuantumCircuit(2, 2)
                qc.h(0)
                qc.cx(0, 1)
                
                # Random basis choices
                alice_basis = random.choice(['rectilinear', 'diagonal'])
                bob_basis = random.choice(['rectilinear', 'diagonal'])
                
                if alice_basis == 'diagonal': qc.h(0)
                if bob_basis == 'diagonal': qc.h(1)
                
                # Optional eavesdropper
                if include_eavesdropping and random.random() < 0.3:
                    qc.measure_all()
                    eve_results = backend.run(qc, shots=1, memory=True).result().get_memory()[0]
                    qc = QuantumCircuit(2, 2)
                    if eve_results[1] == '1': qc.x(0)
                    if eve_results[0] == '1': qc.x(1)
                    if alice_basis == 'diagonal': qc.h(0)
                    if bob_basis == 'diagonal': qc.h(1)
                
                qc.measure(0, 0); qc.measure(1, 1)
                measurements = backend.run(qc, shots=1, memory=True).result().get_memory()[0]
                
                if alice_basis == bob_basis:
                    bob_key.append(int(measurements[0]))
                    bit_index += 1
        else:
            # Original random generation logic
            alice_key, bob_key = [], []
            
            while len(alice_key) < key_length:
                qc = QuantumCircuit(2, 2)
                qc.h(0)
                qc.cx(0, 1)
                
                # Random basis choices
                alice_basis = random.choice(['rectilinear', 'diagonal'])
                bob_basis = random.choice(['rectilinear', 'diagonal'])
                
                if alice_basis == 'diagonal': qc.h(0)
                if bob_basis == 'diagonal': qc.h(1)
                
                # Optional eavesdropper
                if include_eavesdropping and random.random() < 0.3:
                    qc.measure_all()
                    eve_results = backend.run(qc, shots=1, memory=True).result().get_memory()[0]
                    qc = QuantumCircuit(2, 2)
                    if eve_results[1] == '1': qc.x(0)
                    if eve_results[0] == '1': qc.x(1)
                    if alice_basis == 'diagonal': qc.h(0)
                    if bob_basis == 'diagonal': qc.h(1)
                
                qc.measure(0, 0); qc.measure(1, 1)
                measurements = backend.run(qc, shots=1, memory=True).result().get_memory()[0]
                
                if alice_basis == bob_basis:
                    alice_key.append(int(measurements[1]))
                    bob_key.append(int(measurements[0]))
        
        return {'alice_key': alice_key, 'bob_key': bob_key, 'protocol': self.name, 'eavesdropping': include_eavesdropping}


# ================================================
# 🛰️ Teleportation-Based QKD
# ================================================
class TeleportationQKD(QKDProtocol):
    """Quantum Teleportation-based QKD"""

    def __init__(self):
        super().__init__("Teleportation QKD", "QKD using quantum teleportation protocol")
    
    def generate_key(self, key_length, include_eavesdropping=False, custom_bits=None):
        """
        Uses quantum teleportation to securely transmit bits.
        Shared entanglement and classical communication ensure correlated results.
        If custom_bits provided, uses those directly as Alice's key.
        """
        backend = Aer.get_backend('qasm_simulator')
        
        # If custom bits provided, use them directly as Alice's key
        if custom_bits:
            custom_bit_list = [int(bit) for bit in custom_bits]
            if len(custom_bit_list) < key_length:
                raise ValueError(f"Custom bits must be at least {key_length} bits long")
            
            # Use custom bits directly as Alice's key
            alice_key = custom_bit_list[:key_length]
            
            # Generate Bob's key through quantum simulation
            bob_key = []
            
            for i in range(key_length):
                # --- Step 1: Setup and secret bit preparation ---
                qc = QuantumCircuit(3, 3)
                secret_bit = alice_key[i]  # Use Alice's custom bit
                if secret_bit == 1: qc.x(0)
                
                # --- Step 2: Create Bell pair between Alice and Bob ---
                qc.h(1); qc.cx(1, 2)
                
                # --- Step 3: Bell measurement by Alice ---
                qc.cx(0, 1); qc.h(0)
                
                # --- Step 4: Optional eavesdropping ---
                if include_eavesdropping and random.random() < 0.2:
                    if random.random() < 0.3:
                        qc.x(random.randint(0, 2))
                
                # --- Step 5: Measure Alice's qubits ---
                qc.measure(0, 0); qc.measure(1, 1)
                alice_measurements = backend.run(qc, shots=1, memory=True).result().get_memory()[0]
                
                # --- Step 6: Bob applies classical corrections ---
                bob_qc = QuantumCircuit(1, 1)
                if alice_measurements[1] == '1': bob_qc.x(0)
                if alice_measurements[0] == '1': bob_qc.z(0)
                bob_qc.measure(0, 0)
                
                bob_bit = int(backend.run(bob_qc, shots=1, memory=True).result().get_memory()[0])
                bob_key.append(bob_bit)
        else:
            # Original random generation logic
            alice_key, bob_key = [], []
            
            for i in range(key_length):
                # --- Step 1: Setup and secret bit preparation ---
                qc = QuantumCircuit(3, 3)
                secret_bit = random.randint(0, 1)
                if secret_bit == 1: qc.x(0)
                
                # --- Step 2: Create Bell pair between Alice and Bob ---
                qc.h(1); qc.cx(1, 2)
                
                # --- Step 3: Bell measurement by Alice ---
                qc.cx(0, 1); qc.h(0)
                
                # --- Step 4: Optional eavesdropping ---
                if include_eavesdropping and random.random() < 0.2:
                    if random.random() < 0.3:
                        qc.x(random.randint(0, 2))
                
                # --- Step 5: Measure Alice's qubits ---
                qc.measure(0, 0); qc.measure(1, 1)
                alice_measurements = backend.run(qc, shots=1, memory=True).result().get_memory()[0]
                
                # --- Step 6: Bob applies classical corrections ---
                bob_qc = QuantumCircuit(1, 1)
                if alice_measurements[1] == '1': bob_qc.x(0)
                if alice_measurements[0] == '1': bob_qc.z(0)
                bob_qc.measure(0, 0)
                
                bob_bit = int(backend.run(bob_qc, shots=1, memory=True).result().get_memory()[0])
                alice_key.append(secret_bit)
                bob_key.append(bob_bit)
        
        return {'alice_key': alice_key, 'bob_key': bob_key, 'protocol': self.name, 'eavesdropping': include_eavesdropping}


# ================================================
# 🌐 Flask API Setup
# ================================================
protocols = {
    'bb84': BB84Protocol(),
    'e91': E91Protocol(),
    'bbm92': BBM92Protocol(),
    'teleportation': TeleportationQKD()
}

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/protocols')
def get_protocols():
    """Return list of available QKD protocols"""
    return jsonify({
        'protocols': {name: {'name': proto.name, 'description': proto.description} 
                     for name, proto in protocols.items()}
    })

@app.route('/run_simulation', methods=['POST'])
def run_simulation():
    """
    Run a simulation for the selected QKD protocol.
    Handles:
    - Quantum key generation (auto key generation or custom bits)
    - Security metric computation (QBER, agreement rate)
    """
    data = request.get_json()
    protocol_name = data.get('protocol', 'bb84')
    key_length = int(data.get('key_length', 20))
    include_eavesdropping = data.get('eavesdropping', False)
    use_custom_bits = data.get('use_custom_bits', False)
    custom_bits = data.get('custom_bits', '')
    
    if protocol_name not in protocols:
        return jsonify({'error': 'Invalid protocol'}), 400
    
    try:
        # 🔑 Key Generation happens here (auto or custom)
        qkd_protocol = protocols[protocol_name]
        if use_custom_bits and custom_bits:
            # Validate custom bits
            if not all(bit in '01' for bit in custom_bits):
                return jsonify({'error': 'Custom bits must contain only 0s and 1s'}), 400
            if len(custom_bits) < key_length:
                return jsonify({'error': f'Custom bits must be at least {key_length} characters long'}), 400
            key_data = qkd_protocol.generate_key(key_length, include_eavesdropping, custom_bits)
        else:
            key_data = qkd_protocol.generate_key(key_length, include_eavesdropping)
        
        # Calculate QBER and other metrics
        metrics = qkd_protocol.calculate_security_metrics(
            key_data['alice_key'], 
            key_data['bob_key'], 
            include_eavesdropping
        )
        
        # Prepare final response
        results = {
            'protocol': key_data['protocol'],
            'alice_key': key_data['alice_key'],
            'bob_key': key_data['bob_key'],
            'key_length': len(key_data['alice_key']),
            'eavesdropping': include_eavesdropping,
            'agreement_rate': f"{metrics['agreement_rate']:.3f}",
            'qber': f"{metrics['qber']:.3f}",
            'is_secure': metrics['is_secure'],
            'security_level': metrics['security_level'],
            'status': 'Secure communication possible' if metrics['is_secure'] else 'Security compromised - abort key exchange'
        }
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/compare_protocols', methods=['POST'])
def compare_protocols():
    """Compare multiple QKD protocols in one request."""
    data = request.get_json()
    key_length = int(data.get('key_length', 20))
    include_eavesdropping = data.get('eavesdropping', False)
    use_custom_bits = data.get('use_custom_bits', False)
    custom_bits = data.get('custom_bits', '')
    
    results = {}
    
    for protocol_name, protocol in protocols.items():
        try:
            # 🔑 Key generation for each protocol (auto or custom)
            if use_custom_bits and custom_bits:
                key_data = protocol.generate_key(key_length, include_eavesdropping, custom_bits)
            else:
                key_data = protocol.generate_key(key_length, include_eavesdropping)
            metrics = protocol.calculate_security_metrics(
                key_data['alice_key'], key_data['bob_key'], include_eavesdropping
            )
            results[protocol_name] = {
                'name': protocol.name,
                'agreement_rate': f"{metrics['agreement_rate']:.3f}",
                'qber': f"{metrics['qber']:.3f}",
                'security_level': metrics['security_level'],
                'is_secure': metrics['is_secure'],
                'key_length': len(key_data['alice_key'])
            }
        except Exception as e:
            results[protocol_name] = {'error': str(e)}
    
    return jsonify(results)


@app.route('/protocol_circuit')
def protocol_circuit():
    """Return ASCII diagram of a representative quantum circuit for a protocol."""
    protocol_name = request.args.get('protocol', 'bb84')
    key_length = int(request.args.get('key_length', 4))
    if protocol_name not in protocols:
        return jsonify({'error': 'Invalid protocol'}), 400
    try:
        proto = protocols[protocol_name]
        circuit_text = proto.get_circuit_text(key_length)
        return jsonify({'protocol': proto.name, 'circuit': circuit_text, 'key_length': key_length})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ================================================
# 🚀 Flask App Entry Point
# ================================================
if __name__ == '__main__':
    print("🌌 Starting Quantum Key Distribution (QKD) Simulation Server...")
    print("📡 Available Protocols: BB84, E91, BBM92, Teleportation QKD")
    print("🔗 Open your browser and go to: http://localhost:5000")
    print("⚡ Server running with debug mode enabled")
    app.run(debug=True, host='0.0.0.0', port=5000)
