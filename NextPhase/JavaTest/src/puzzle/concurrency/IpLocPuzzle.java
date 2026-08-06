package puzzle.concurrency;
import puzzle.Puzzle;

import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;

/**
 * Copy a file using Java NIO channels and a ByteBuffer.
 * NOTE: NIO file-copy demo (name is misleading -- not IP geolocation).
 */
public class IpLocPuzzle implements Puzzle {

    /**
     * Copy the project file to a sibling path using the same NIO pattern as {@link NioPuzzle}.
     */
    @Override
    public void resolve() {
        try {
            copyFile("JavaTest.iml", "JavaTest_cp.iml");
        } catch (IOException e) {
            throw new IllegalStateException("Failed to copy JavaTest.iml in IpLocPuzzle.", e);
        }
    }

    /**
     * Copy a file through buffered channel reads and writes.
     */
    private void copyFile(String inputPath, String outputPath) throws IOException {
        try (FileInputStream fin = new FileInputStream(inputPath);
             FileOutputStream fout = new FileOutputStream(outputPath);
             FileChannel inputChannel = fin.getChannel();
             FileChannel outputChannel = fout.getChannel()) {
            ByteBuffer buffer = ByteBuffer.allocate(100);
            while (true) {
                buffer.clear();
                int read = inputChannel.read(buffer);
                if (read <= 0) {
                    break;
                }
                buffer.flip();
                outputChannel.write(buffer);
            }
        }
    }
}
