package puzzle.stack;
import puzzle.Puzzle;

import java.util.*;

/**
 * Simulate nested begin / commit / rollback transactions and output the surviving commands.
 * Approach: a stack of transaction buffers; each buffered command carries a committed flag.
 *   commit  -> pop the top level, mark all its commands committed, promote them to the parent (or output);
 *   rollback-> pop the top level, keep ONLY already-committed commands (Model B: an inner commit is
 *              permanent and survives an outer rollback), discard the rest.
 * Output preserves the original command order. Complexity: Time O(n), Space O(n).
 * Created by qingjuntian on 6/26/16.
 */
public class CommitStatementPuzzle implements Puzzle {

    @Override
    public void resolve() {
        List<String> commands = new LinkedList<>();
        commands.add("Insert A");
        commands.add("begin");
        commands.add("insert B");
        commands.add("insert C");
        commands.add("Update A");
        commands.add("begin");
        commands.add("insert E");
        commands.add("rollback");
        commands.add("commit");
        commands.add("insert D");
        commands.add("begin");
        commands.add("insert B");
        commands.add("insert C");
        commands.add("rollback");
        List<String> commitCommand = findCommitedCommands(commands);
        System.out.println(commitCommand);
    }

    private List<String> findCommitedCommands(List<String> commands) {
        List<String> ret = new LinkedList<>();
        // Stack of open transactions (LIFO). Each buffers its commands; an item is marked
        // committed=true once permanently committed, so it survives an OUTER rollback (Model B).
        Deque<List<Item>> stack = new ArrayDeque<>();
        for (String raw : commands) {
            String command = normalizeCommand(raw);
            if ("begin".equals(command)) {
                stack.push(new ArrayList<>());                        // open a nested transaction
            } else if ("commit".equals(command)) {
                if (stack.isEmpty()) continue;                        // ignore unmatched commit
                List<Item> top = stack.pop();
                for (Item it : top) it.committed = true;              // everything here is now permanent
                if (stack.isEmpty()) { for (Item it : top) ret.add(it.cmd); }
                else stack.peek().addAll(top);                        // promote to the parent transaction
            } else if ("rollback".equals(command)) {
                if (stack.isEmpty()) continue;                        // ignore unmatched rollback
                List<Item> top = stack.pop();
                List<Item> kept = new ArrayList<>();
                for (Item it : top) if (it.committed) kept.add(it);  // keep only already-committed (Model B)
                if (stack.isEmpty()) { for (Item it : kept) ret.add(it.cmd); }
                else stack.peek().addAll(kept);
            } else if (!stack.isEmpty()) {
                stack.peek().add(new Item(command, false));           // buffer inside current transaction
            } else {
                ret.add(command);                                    // outside any transaction -> output
            }
        }
        // flush committed commands still stuck in any unclosed transactions (outer -> inner)
        for (Iterator<List<Item>> lvl = stack.descendingIterator(); lvl.hasNext(); )
            for (Item it : lvl.next()) if (it.committed) ret.add(it.cmd);
        return ret;
    }

    private static final class Item {
        final String cmd;
        boolean committed;
        Item(String cmd, boolean committed) { this.cmd = cmd; this.committed = committed; }
    }

    private String normalizeCommand(String command) {
        return command.toLowerCase().trim();
    }


}
