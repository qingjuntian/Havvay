package puzzle.concurrency;
import puzzle.Puzzle;

import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;

/**
 * Copy a file using Java NIO FileChannel and ByteBuffer.
 * NOTE: NIO file-copy demo.
 */
public class NioPuzzle implements Puzzle {

    /**
     * Copy the project file to a sibling path using a fixed-size direct buffer.
     */
    @Override
    public void resolve() {
        try {
            copyFile("JavaTest.iml", "JavaTest_cp.iml");
        } catch (IOException e) {
            throw new IllegalStateException("Failed to copy JavaTest.iml with NIO.", e);
        }
    }

    /**
     * Copy a file by repeatedly filling the buffer from the input channel and draining it to the output channel.
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
