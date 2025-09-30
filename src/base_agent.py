"""
Base agent class and agent orchestration system.
Implements the core agent architecture with LangGraph integration.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
from loguru import logger

# from langchain.schema import BaseMessage, HumanMessage, SystemMessage  # Reserved for future use
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

from models import AgentMessage, AgentState
from state_manager import StateManager


class BaseAgent(ABC):
    """Base class for all logistics agents"""
    
    def __init__(self, name: str, state_manager: StateManager, llm: Optional[ChatOpenAI] = None):
        self.name = name
        self.state_manager = state_manager
        self.llm = llm or ChatOpenAI(temperature=0)
        self.messages: List[AgentMessage] = []
        
        # Initialize agent state
        self.state_manager.update_agent_state(self.name, AgentState.PLANNING)
    
    @abstractmethod
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main processing method - must be implemented by each agent"""
        pass
    
    def send_message(self, receiver: str, message_type: str, payload: Dict[str, Any]):
        """Send message to another agent"""
        import uuid
        from src.models import MessageType
        
        # Convert string message_type to MessageType enum
        try:
            msg_type = MessageType(message_type)
        except ValueError:
            # If not a valid enum value, use SYSTEM_ALERT as fallback
            logger.warning(f"Invalid message type '{message_type}', using SYSTEM_ALERT")
            msg_type = MessageType.SYSTEM_ALERT
        
        message = AgentMessage(
            id=str(uuid.uuid4()),
            sender_agent=self.name,
            recipient_agent=receiver,
            message_type=msg_type,
            payload=payload
        )
        self.messages.append(message)
        logger.info(f"{self.name} -> {receiver}: {message_type}")
        return message
    
    def receive_message(self, message: AgentMessage):
        """Receive and process message from another agent"""
        logger.info(f"{self.name} received: {message.message_type} from {message.sender_agent}")
        self.messages.append(message)
        return self._handle_message(message)
    
    def _handle_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle incoming message - override in subclasses"""
        return {"status": "received", "message_id": len(self.messages)}
    
    def update_state(self, state: AgentState):
        """Update agent's operational state"""
        self.state_manager.update_agent_state(self.name, state)
        logger.debug(f"{self.name} state updated to {state.value}")
    
    def get_system_state(self):
        """Get current system state"""
        return self.state_manager.get_system_state()


class AgentOrchestrator:
    """Orchestrates multi-agent workflow using LangGraph"""
    
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
        self.agents: Dict[str, BaseAgent] = {}
        self.workflow = None
        self.message_queue: List[AgentMessage] = []
        self._processed_orders = set()  # Track orders we've already processed
        self._current_step_count = 0
        
    def register_agent(self, agent: BaseAgent):
        """Register an agent with the orchestrator"""
        self.agents[agent.name] = agent
        logger.info(f"Registered agent: {agent.name}")
    
    def build_workflow(self):
        """Build the LangGraph workflow for agent coordination"""
        workflow = StateGraph(dict)
        
        # Add nodes for each agent
        for agent_name, agent in self.agents.items():
            workflow.add_node(agent_name, agent.process)
        
        # Add orchestration logic
        workflow.add_node("orchestrator", self._orchestrate)
        
        # Set entry point
        workflow.set_entry_point("orchestrator")
        
        # Add conditional edges based on agent dependencies
        workflow.add_conditional_edges(
            "orchestrator",
            self._route_to_agents,
            list(self.agents.keys()) + [END]
        )
        
        # Agents report back to orchestrator
        for agent_name in self.agents.keys():
            workflow.add_edge(agent_name, "orchestrator")
        
        # Compile workflow (config not supported in this version)
        self.workflow = workflow.compile()
        logger.info("Agent workflow compiled successfully")
    
    def _orchestrate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Main orchestration logic"""
        logger.info("Orchestrator processing workflow step")
        
        # Initialize step counter to prevent infinite loops
        step_count = state.get("step_count", 0) + 1
        state["step_count"] = step_count
        self._current_step_count = step_count  # Track in instance
        
        # Safety check: if too many steps, force end
        if step_count > 20:
            logger.warning(f"Orchestrator reached maximum steps ({step_count}), forcing end")
            state["force_end"] = True
            return state
        
        # Update orchestrator state
        self.state_manager.update_agent_state("orchestrator", AgentState.EXECUTING)
        
        # Process message queue
        self._process_message_queue()
        
        # Determine next actions based on system state
        system_state = self.state_manager.get_system_state()
        
        # Add orchestration decisions to state
        state["orchestrator_decisions"] = self._make_decisions(system_state)
        state["timestamp"] = datetime.now().isoformat()
        
        return state
    
    def _route_to_agents(self, state: Dict[str, Any]) -> str:
        """Determine which agent should process next"""
        # Check for forced end condition
        if state.get("force_end", False):
            logger.info("Workflow forced to end due to step limit")
            return END
            
        decisions = state.get("orchestrator_decisions", {})
        
        # Route based on priorities and system state
        if decisions.get("new_orders"):
            logger.debug("Routing to order_ingestion_agent for new orders")
            return "order_ingestion_agent"
        elif decisions.get("needs_assignment"):
            logger.debug("Routing to vehicle_assignment_agent for assignments")
            return "vehicle_assignment_agent"
        elif decisions.get("needs_routing"):
            logger.debug("Routing to route_planning_agent for routing")
            return "route_planning_agent"
        elif decisions.get("has_exceptions"):
            logger.debug("Routing to exception_handling_agent for exceptions")
            return "exception_handling_agent"
        else:
            logger.info("No pending actions, ending workflow")
            return END
    
    def _make_decisions(self, system_state) -> Dict[str, bool]:
        """Make high-level orchestration decisions"""
        decisions = {
            "new_orders": False,
            "needs_assignment": False,
            "needs_routing": False,
            "has_exceptions": False
        }
        
        # Get current step count to prevent infinite loops
        current_step = getattr(self, '_current_step_count', 0)
        
        # If we've been running too long, only handle exceptions
        if current_step > 15:
            failed_orders = [o for o in system_state.orders.values() if o.state.value == "failed"]
            decisions["has_exceptions"] = len(failed_orders) > 0
            logger.warning(f"Step {current_step}: Only handling exceptions to prevent infinite loop")
            return decisions
        
        # Normal decision logic
        # Check for new orders that haven't been processed yet
        new_orders = [o for o in system_state.orders.values() 
                     if o.state.value == "new" and o.id not in self._processed_orders]
        decisions["new_orders"] = len(new_orders) > 0
        
        # If we found new orders, mark them as being processed
        if decisions["new_orders"]:
            for order in new_orders:
                self._processed_orders.add(order.id)
                logger.debug(f"Marking order {order.id} as being processed")
        
        # Check for orders that need vehicle assignment (processed but not assigned)
        if not decisions["new_orders"]:  # Only check if not processing new orders
            ready_orders = [o for o in system_state.orders.values() 
                           if o.state.value == "new" and o.id in self._processed_orders]
            decisions["needs_assignment"] = len(ready_orders) > 0
        
        # Check for orders that need routing (assigned but not yet en_route)
        assigned_orders = [o for o in system_state.orders.values() if o.state.value == "assigned"]
        decisions["needs_routing"] = len(assigned_orders) > 0 and not decisions["new_orders"] and not decisions["needs_assignment"]
        
        # Check for failed orders that need exception handling
        failed_orders = [o for o in system_state.orders.values() if o.state.value == "failed"]
        decisions["has_exceptions"] = len(failed_orders) > 0
        
        logger.info(f"Step {current_step}: Orchestrator decisions: {decisions}")
        logger.info(f"Processed orders: {list(self._processed_orders)}")
        return decisions
    
    def _process_message_queue(self):
        """Process pending inter-agent messages"""
        while self.message_queue:
            message = self.message_queue.pop(0)
            if message.receiver in self.agents:
                self.agents[message.receiver].receive_message(message)
    
    def route_message(self, message: AgentMessage):
        """Route message between agents"""
        self.message_queue.append(message)
    
    def run_workflow(self, initial_input: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute the agent workflow with timeout protection"""
        if not self.workflow:
            self.build_workflow()
        
        # Reset tracking for new workflow run
        self._processed_orders.clear()
        self._current_step_count = 0
        
        input_data = initial_input or {"action": "process_system", "step_count": 0}
        
        try:
            # Set a hard limit on workflow execution time
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("Workflow execution timed out after 30 seconds")
            
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(30)  # 30 second timeout
            
            result = self.workflow.invoke(input_data)
            signal.alarm(0)  # Cancel the alarm
            
            logger.info("Workflow execution completed successfully")
            return result
        except TimeoutError as e:
            logger.error(f"Workflow execution timed out: {e}")
            return {"error": "Workflow timed out", "timeout": True}
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            # Return a more graceful result instead of raising
            return {"error": str(e), "failed": True}
    
    def get_agent_status(self) -> Dict[str, str]:
        """Get status of all registered agents"""
        status = {}
        for agent_name in self.agents.keys():
            agent_state = self.state_manager.get_agent_state(agent_name)
            status[agent_name] = agent_state.value if agent_state else "unknown"
        return status