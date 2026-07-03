import simpy
import datetime
import numpy as np
import pandas as pd
from typing import Any, Optional, Tuple

#Manually coding the Generic Process class so that I know exactly about it's behaviour. The LLM will not be used to code the 
#entire thing but only very small bits and pieces of code that I know is valid and I know the exact explanations of my 
#model limitations

class manual_generic_process(simpy.events.Process):
    '''
    This class extends the simpy.events.Process function and makes it more useful
    For my personal implementation of the DES for the wire mesh and the cytopathology simulation. I have custom needs
    such as timekeeping etc which I want to be able to implement in a generic way. Also this will work better
    with a UI that I plan to build later on. 
    '''
    def __init__(self, env, process_name, resources_requested, service_time_params,
                 is_batched = False, batch_size = None, next_process = None):
        self.env = env
        self.process_name = process_name # A string
        self.resources_requested = resources_requested # List
        self.service_time_params = service_time_params # Dictionary: {'distribution': '...', 'params': {...}}
        self.is_batched = is_batched # Boolean
        self.batch_size = batch_size # Integer
        self.batch = []
        self.next_process = next_process # Assign the passed parameter

    def _resolve_service_time_params(self, entity):
        """
        Resolve optional keyed layouts:
        - by_size: branch on entity.size (e.g. histo fixation).
        - by_case_complexity: branch on entity.case_complexity (e.g. reporting).
        """
        stp = self.service_time_params
        if not isinstance(stp, dict):
            return stp
        if "by_size" in stp:
            by_sz = stp["by_size"]
            sz = getattr(entity, "size", "small")
            branch = by_sz.get(sz) or by_sz.get("small")
            if branch is None:
                raise KeyError(
                    f"No service_time branch for size={sz!r} and no 'small' fallback in by_size"
                )
            return branch
        if "by_case_complexity" in stp:
            by_cc = stp["by_case_complexity"]
            cc = getattr(entity, "case_complexity", "low")
            branch = by_cc.get(cc) or by_cc.get("low")
            if branch is None:
                raise KeyError(
                    f"No service_time branch for case_complexity={cc!r} and no 'low' fallback in by_case_complexity"
                )
            return branch
        return stp

    def _parse_resource_spec(self, res_spec, entity_count: int = 1) -> Tuple[Any, Optional[str], float]:
        """
        Parse a resource specification.

        Supported forms:
        - resource
        - (resource, amount) for containers
        - (resource, task) for TaskScheduledResource
        """
        if not isinstance(res_spec, tuple):
            return res_spec, None, float(entity_count)

        res, second = res_spec[0], res_spec[1]
        if isinstance(second, str):
            return res, second, float(entity_count)
        return res, None, float(second) * entity_count

    def _task_window_fits(self, res, task: str, required_minutes: float) -> bool:
        now_dt = res._sim_time_to_datetime(self.env.now)
        if not res.task_schedules[task].is_available_at(now_dt):
            return False
        return res._minutes_remaining_in_task_window(task, now_dt) >= required_minutes

    def _acquire_in_order(self, entity_count: int, gate_service_time: float):
        """Acquire task-tagged resources first (with window gating), then other resources."""
        acquired = []
        for res_spec in self.resources_requested:
            res, task, amount = self._parse_resource_spec(res_spec, entity_count)
            if task is not None and hasattr(res, "wait_until_can_start"):
                task_req = None
                for _ in range(6):
                    yield from res.wait_until_can_start(task, gate_service_time)
                    req = res.request()
                    yield req
                    if self._task_window_fits(res, task, gate_service_time):
                        task_req = req
                        break
                    res.release(req)
                if task_req is None:
                    yield from res.wait_until_can_start(task, gate_service_time)
                    task_req = res.request()
                    yield task_req
                acquired.append(task_req)
            elif hasattr(res, "level"):
                req = res.get(amount)
                yield req
                acquired.append(req)
            else:
                req = res.request()
                yield req
                acquired.append(req)
        return acquired

    def _request_all(self, entity_count):
        """Legacy helper without task-window gating (containers / plain resources)."""
        requests = []
        for res_spec in self.resources_requested:
            res, task, amount = self._parse_resource_spec(res_spec, entity_count)
            if hasattr(res, "level"):
                requests.append(res.get(amount))
            else:
                requests.append(res.request())
        return requests

    def _release_all(self, requests):
        """Helper to release only the Resource-type objects (skips Containers)."""
        for res_spec, req in zip(self.resources_requested, requests):
            res, _, _ = self._parse_resource_spec(res_spec, entity_count=1)
            if not hasattr(res, 'level'):
                res.release(req)
        
    def add_item(self, entity):
        '''
        Common entry point for Entity_Generator or other processes.
        Routes to the correct runner based on batching configuration.
        '''
        if self.is_batched:
            return self.env.process(self.run_batch(entity))
        else:
            return self.env.process(self.run_non_batch(entity))
        
    def get_service_time(self, params_dict):
        dist = params_dict.get('distribution')
        params = params_dict.get('params', {})
        
        if dist == "constant":
            if isinstance(params, (int, float)):
                return params
            elif isinstance(params, list):
                return params[0]
            return params.get('mean', params.get('rate', params.get('value', 0)))
        elif dist == "exponential":
            if isinstance(params, (int, float)):
                return np.random.exponential(params)
            elif isinstance(params, list):
                return np.random.exponential(params[0])
            return np.random.exponential(params.get('mean', params.get('rate', 1)))
        elif dist == "normal":
            if isinstance(params, list):
                return np.random.normal(params[0], params[1])
            return np.random.normal(params.get('mean', 0), params.get('sd', 1))
        elif dist == "uniform":
            if isinstance(params, list):
                return np.random.uniform(params[0], params[1])
            return np.random.uniform(params.get('min', 0), params.get('max', 1))
        elif dist == 'beta':
            if isinstance(params, list):
                return np.random.beta(params[0], params[1])
            return np.random.beta(params.get('alpha', 1), params.get('beta', 1))
        elif dist == 'pert' or dist == 'triangular':
            if isinstance(params, list):
                return np.random.triangular(params[0], params[1], params[2])
            return np.random.triangular(params.get('min', 0), params.get('mode', params.get('mean', 1)), params.get('max', 2)) 
        else:
            raise ValueError(f"Invalid service time distribution: {dist}")

    def _pessimistic_service_time(self, params_dict) -> float:
        """Upper-bound service time used for task-window gating (Option A)."""
        dist = params_dict.get("distribution")
        params = params_dict.get("params", {})
        if dist == "triangular" and isinstance(params, list) and len(params) >= 3:
            return float(max(params))
        if dist == "pert" and isinstance(params, list) and len(params) >= 3:
            return float(max(params))
        if dist == "uniform" and isinstance(params, list) and len(params) >= 2:
            return float(params[1])
        if dist == "normal" and isinstance(params, list) and len(params) >= 2:
            return float(params[0]) + 3.0 * float(params[1])
        return float(self.get_service_time(params_dict))
        
    
    def is_batch_complete(self, entity):
        if self.is_batched:
            self.batch.append(entity)
            if len(self.batch) == self.batch_size:
                ready_batch = self.batch[:]  # Capture the current set
                self.batch = []              # Clear for the next batch
                return ready_batch
            return None
    
    def run_non_batch(self, entity):
        '''
        This function handles the execution of the process, this is where the main execution logic sits
        '''
        start_q_time = self.env.now
        
        # Initialize dictionaries if they don't exist
        if not hasattr(entity, 'queue_entry_time'): entity.queue_entry_time = {}
        if not hasattr(entity, 'process_start_time'): entity.process_start_time = {}
        if not hasattr(entity, 'process_end_time'): entity.process_end_time = {}

        entity.queue_entry_time[self.process_name] = self.env.now

        resolved_params = self._resolve_service_time_params(entity)
        gate_service_time = self._pessimistic_service_time(resolved_params)
        requests = yield from self._acquire_in_order(1, gate_service_time)

        entity.process_start_time[self.process_name] = self.env.now
        service_time = self.get_service_time(resolved_params)
        yield self.env.timeout(service_time)
        
        # End of process
        entity.process_end_time[self.process_name] = self.env.now
        
        # Release Resources (Containers are consumed and not released)
        self._release_all(requests)
            
        # Move to next stage
        if self.next_process is not None:
            target = self.next_process(entity) if callable(self.next_process) else self.next_process
            if target:
                self.env.process(target.run_non_batch(entity) if not target.is_batched else target.run_batch(entity))
        else:
            print(f"[{self.env.now:.2f}] {entity.id} has completed all processes.")
                
                
    def run_batch(self, entity):
        '''
        This is a special function to be called when is_batched == True
        '''   
        # Initialize dictionaries on arrival
        if not hasattr(entity, 'queue_entry_time'): entity.queue_entry_time = {}
        if not hasattr(entity, 'process_start_time'): entity.process_start_time = {}
        if not hasattr(entity, 'process_end_time'): entity.process_end_time = {}
        
        entity.queue_entry_time[self.process_name] = self.env.now
        
        # Check if this entity completes the current batch
        ready_batch = self.is_batch_complete(entity)
        
        if ready_batch is not None:
            resolved_params = self._resolve_service_time_params(ready_batch[0])
            gate_service_time = self._pessimistic_service_time(resolved_params)
            requests = yield from self._acquire_in_order(len(ready_batch), gate_service_time)

            for ent in ready_batch:
                ent.process_start_time[self.process_name] = self.env.now

            yield self.env.timeout(self.get_service_time(resolved_params))
            
            #Note the timestamp for all the entities in the batch at the time that they exit the process
            for ent in ready_batch:
                ent.process_end_time[self.process_name] = self.env.now
            
            # Release the Resources correctly (skips Containers)
            self._release_all(requests)
                
            # Move the entities to the next step
            for ent_in_batch in ready_batch:
                if self.next_process is not None:
                    if callable(self.next_process):
                        # Branching Logic: self.next_process is a function/lambda 
                        # that returns the next process object
                        target = self.next_process(ent_in_batch)
                        if target:
                            self.env.process(target.run_non_batch(ent_in_batch) if not target.is_batched else target.run_batch(ent_in_batch))
                    else:
                        # Linear Logic: self.next_process is the next station
                        target = self.next_process
                        self.env.process(target.run_non_batch(ent_in_batch) if not target.is_batched else target.run_batch(ent_in_batch))
                else:
                    # Final Stage: The simulation ends for this entity
                    print(f"[{self.env.now:.2f}] {ent_in_batch.id} has completed all processes.")
            
                










                
def run_mock_sim():
    """
    Test simulation:
    Mesh -> Cutting (Linear, 1 technician) -> Trimming (Batched in pairs, 1 technician)
    """
    env = simpy.Environment()
    
    # 1. Setup Resources
    technician = simpy.Resource(env, capacity=2)
    
    # 2. Setup Entities
    class MockMesh:
        def __init__(self, name):
            self.id = name
            self.end_time = {}

    # 3. Setup Processes
    # Trimming is the 2nd stage (Batched in 2s)
    trimming = manual_generic_process(
        env=env,
        process_name="trimming",
        resources_requested=[technician],
        service_time_params={
            'distribution': 'constant',
            'params': {'rate': 30}
        },
        is_batched=True,
        batch_size=2
    )
    
    # Cutting is the 1st stage (Not batched)
    cutting = manual_generic_process(
        env=env,
        process_name="cutting",
        resources_requested=[technician],
        service_time_params={
            'distribution': 'constant',
            'params': {'rate': 20}
        },
        is_batched=False,
        next_process=trimming
    )

    # 4. Generator function to feed meshes into the system
    all_meshes = []
    def mesh_generator(env, target_process):
        for i in range(10):
            mesh = MockMesh(f"WM-000{i+1}")
            all_meshes.append(mesh) # Keep track for final summary
            print(f"[{env.now:.2f}] {mesh.id} arrived.")
            # Start the cutting process for this mesh
            env.process(target_process.run_non_batch(mesh))
            yield env.timeout(10) # Next mesh arrives in 10 mins

    # 5. Start the generator and run
    env.process(mesh_generator(env, cutting))
    
    print("--- Starting Mock Simulation ---")
    env.run(until=500)
    print("--- Simulation Complete ---\n")
    
    # 6. Log results as a DataFrame and reorder columns as requested
    results_list = []
    for m in all_meshes:
        for proc in ["cutting", "trimming"]:
            results_list.append({
                "Mesh ID": m.id,
                "Process": proc,
                "entry": m.queue_entry_time.get(proc, 0),
                "start": m.process_start_time.get(proc, 0),
                "end": m.process_end_time.get(proc, 0)
            })
    
    # Pivot the DataFrame so each Mesh ID is one row
    df = pd.DataFrame(results_list)
    df_pivot = df.pivot(index='Mesh ID', columns='Process')
    
    # Flatten MultiIndex and rename for a cleaner look (e.g., cutting_start)
    df_pivot.columns = [f"{proc}_{metric}" for metric, proc in df_pivot.columns]
    df_pivot.reset_index(inplace=True)
    
    # Sort columns into the exact order requested
    cols_order = [
        'Mesh ID', 
        'cutting_start', 'cutting_end', 'cutting_wait',
        'trimming_start', 'trimming_end', 'trimming_wait'
    ]
    df_pivot = df_pivot[cols_order]
    
    print("\n--- Simulation Results (Pivoted & Ordered) ---")
    print(df_pivot.to_string(index=False))
    
    return df_pivot

if __name__ == "__main__":
    df_results = run_mock_sim()